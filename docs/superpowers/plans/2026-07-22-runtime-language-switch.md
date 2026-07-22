# Runtime Language Switch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在单一 PastePeek EXE 中加入 `zh-CN`/`en-US` 运行时语言切换，覆盖 HUD、托盘、预测、预览和主动操作反馈，并保持默认中文与剪贴板安全行为不变。

**Architecture:** 新增无 IO 的 `src/i18n.py`，集中维护语言归一化、静态文案和标签；UI 组件保存当前语言并在菜单切换时发出信号。`PastePeekApp` 将语言传给 `OutcomePredictor`、`PreviewRenderer` 和 `text_toolkit`，只根据内存中的当前剪贴板快照重建 `AppOutput`，不写入剪贴板。

**Tech Stack:** Python 3.12、PySide6、pytest、现有 PyInstaller/Windows 托盘和剪贴板管线。

## Global Constraints

- 支持语言严格为 `zh-CN` 和 `en-US`，默认 `zh-CN`；非法值回退默认语言。
- 语言保存到现有 `%LOCALAPPDATA%\\PastePeek\\config.json`，旧配置缺少字段仍可启动。
- 不翻译用户剪贴板正文，不引入联网翻译、云服务、剪贴板历史或第二套 EXE。
- 语言切换不清空、改写或重新获取剪贴板；安全拒绝、序列校验和失败回滚语义保持不变。
- 新增代码注释和项目说明使用简体中文；直接调用主动操作函数时默认返回中文消息。
- 每个任务必须先写失败测试并运行确认 RED，再写最小实现并运行 GREEN。

---

### Task 1: 本地化核心模块

**Files:**
- Create: `src/i18n.py`
- Create: `tests/test_i18n.py`

**Interfaces:**
- Produces `SUPPORTED_LANGUAGES: tuple[str, ...]`, `DEFAULT_LANGUAGE: str`。
- Produces `normalize_language(value: object) -> str`。
- Produces `translate(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str`。
- Produces `content_type_label(key: str, language: str) -> str`、`target_label(key: str, language: str, compact: bool = False) -> str`、`target_group_label(key: str, language: str) -> str`、`risk_label(level: str, language: str) -> str`。

- [ ] **Step 1: Write the failing tests**

```python
from src.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    content_type_label,
    normalize_language,
    risk_label,
    target_label,
    translate,
)


def test_language_values_and_invalid_fallback():
    assert SUPPORTED_LANGUAGES == ("zh-CN", "en-US")
    assert DEFAULT_LANGUAGE == "zh-CN"
    assert normalize_language("en-US") == "en-US"
    assert normalize_language("en") == "en-US"
    assert normalize_language("invalid") == DEFAULT_LANGUAGE
    assert normalize_language(None) == DEFAULT_LANGUAGE


def test_static_labels_follow_language():
    assert content_type_label("rich_text", "zh-CN") == "富文本"
    assert content_type_label("rich_text", "en-US") == "Rich text"
    assert target_label("code_editor", "en-US") == "Code editor"
    assert target_label("code_editor", "en-US", compact=True) == "Code"
    assert risk_label("high", "en-US") == "High risk"
    assert "Language" in translate("language_menu", "en-US")


def test_formatting_does_not_leak_internal_key():
    message = translate("removed_tracking", "en-US", count=2, names="utm_source, ref")
    assert message == "Removed 2 tracking parameters: utm_source, ref"
    assert translate("missing_key", "en-US") == "PastePeek"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `py -3.12 -m pytest tests/test_i18n.py -q`

Expected: FAIL because `src.i18n` and its public functions do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
SUPPORTED_LANGUAGES = ("zh-CN", "en-US")
DEFAULT_LANGUAGE = "zh-CN"


def normalize_language(value: object) -> str:
    if value in SUPPORTED_LANGUAGES:
        return str(value)
    if isinstance(value, str) and value.lower() == "en":
        return "en-US"
    return DEFAULT_LANGUAGE


def translate(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    locale = normalize_language(language)
    template = _MESSAGES.get(locale, {}).get(key)
    if template is None:
        template = _MESSAGES[DEFAULT_LANGUAGE].get(key, "PastePeek")
    return template.format(**kwargs)
```

Fill `_MESSAGES` with all HUD, tray, action, preview and error keys used by later tasks; keep Chinese and English values side by side and never return a raw internal key.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `py -3.12 -m pytest tests/test_i18n.py -q`

Expected: all tests pass with no warnings.

- [ ] **Step 5: Commit**

```bash
git add src/i18n.py tests/test_i18n.py
git commit -m "feat: 增加运行时本地化核心"
```

### Task 2: 配置和预测矩阵本地化

**Files:**
- Modify: `src/explainer/outcome_predictor.py:23-470`
- Modify: `src/models/types.py:74-115`
- Modify: `tests/test_outcome.py`
- Create: `tests/test_outcome_i18n.py`

**Interfaces:**
- `OutcomePredictor.generate(content_type: str, target: str = "word", language: str = DEFAULT_LANGUAGE) -> AppOutput`。
- `CONTENT_TYPES`、`TARGET_APPS`、`TARGET_LABELS` 和 `TARGET_GROUPS` 的中文常量保持兼容；英文通过 `src.i18n` 标签函数获取。

- [ ] **Step 1: Write the failing tests**

```python
from src.explainer.outcome_predictor import OutcomePredictor


def test_english_prediction_contains_no_generated_chinese():
    output = OutcomePredictor().generate("rich_text", "terminal", language="en-US")
    generated = " ".join([output.content_type_label, output.prediction, output.why,
                           output.suggestion, *output.breakdown])
    assert "Rich text" in generated
    assert "Terminal" in generated
    assert not any("\u4e00" <= char <= "\u9fff" for char in generated)


def test_language_does_not_change_risk_or_action_keys():
    zh = OutcomePredictor().generate("plain_text", "terminal", language="zh-CN")
    en = OutcomePredictor().generate("plain_text", "terminal", language="en-US")
    assert (zh.risk_level, zh.primary_target) == (en.risk_level, en.primary_target)
```

- [ ] **Step 2: Run tests to verify RED**

Run: `py -3.12 -m pytest tests/test_outcome_i18n.py -q`

Expected: FAIL because `generate` ignores the language and returns Chinese labels.

- [ ] **Step 3: Write minimal implementation**

Add an English entry table keyed by `(content_type, target)` with the same risk level and action semantics as `COMPATIBILITY_MATRIX`. In `generate`, normalize the language, select the English entry for `en-US`, and use `content_type_label` for the display type. Keep the existing Chinese map as the default path so all current tests remain unchanged.

- [ ] **Step 4: Run focused and existing outcome tests**

Run: `py -3.12 -m pytest tests/test_outcome_i18n.py tests/test_outcome.py -q`

Expected: new English tests and all existing Chinese outcome assertions pass.

- [ ] **Step 5: Commit**

```bash
git add src/explainer/outcome_predictor.py src/models/types.py tests/test_outcome.py tests/test_outcome_i18n.py
git commit -m "feat: 本地化粘贴结果预测"
```

### Task 3: 预览渲染本地化

**Files:**
- Modify: `src/explainer/preview_renderer.py:249-526`
- Modify: `tests/test_preview_renderer.py`
- Create: `tests/test_preview_i18n.py`

**Interfaces:**
- `PreviewRenderer.render(content, target, preview_data=None, language=DEFAULT_LANGUAGE) -> RenderedPreview`。
- Existing positional calls remain valid; `language` is keyword-only after `preview_data`.

- [ ] **Step 1: Write the failing tests**

```python
from src.explainer.preview_renderer import ClipboardContent, PreviewRenderer


def test_english_preview_localizes_renderer_owned_labels_but_keeps_user_text():
    result = PreviewRenderer().render(
        ClipboardContent(text="用户原文", content_type="plain_text"),
        "terminal",
        {"summary": "Pastes as plain text", "risks": [], "render_type": "real"},
        language="en-US",
    )
    assert "Terminal preview" in result.html
    assert "用户原文" in result.html
    assert "终端预览" not in result.html
```

- [ ] **Step 2: Run tests to verify RED**

Run: `py -3.12 -m pytest tests/test_preview_i18n.py -q`

Expected: FAIL because `render` has no language parameter and renderer labels are Chinese.

- [ ] **Step 3: Write minimal implementation**

Thread the normalized language through `_render_safe`, `_fallback_checklist` and all renderer-owned label helpers. Translate only fixed labels such as empty content, Markdown preview, terminal preview, checklist headings and default risks; leave `content.text` and sanitized HTML untouched.

- [ ] **Step 4: Run focused preview regression**

Run: `py -3.12 -m pytest tests/test_preview_i18n.py tests/test_preview_renderer.py tests/test_preview_safety.py -q`

Expected: English and existing Chinese preview tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/explainer/preview_renderer.py tests/test_preview_renderer.py tests/test_preview_i18n.py
git commit -m "feat: 本地化粘贴预览"
```

### Task 4: 主动操作反馈本地化

**Files:**
- Modify: `src/manipulator/text_toolkit.py:86-304`
- Modify: `src/ui/app.py:177-498`
- Modify: `tests/test_text_toolkit.py`
- Modify: `tests/test_text_toolkit_contract.py`
- Create: `tests/test_action_i18n.py`

**Interfaces:**
- `clean_url(*, expected_sequence: int | None = None, language: str = DEFAULT_LANGUAGE) -> tuple[bool, str]`。
- `strip_formats(*, expected_sequence: int | None = None, language: str = DEFAULT_LANGUAGE) -> tuple[bool, str]`。
- `merge_lines(*, expected_sequence: int | None = None, language: str = DEFAULT_LANGUAGE) -> tuple[bool, str]`。
- `PastePeekApp.set_language(language: str) -> str` returns the normalized language and re-emits the cached output when available.

- [ ] **Step 1: Write the failing tests**

```python
def test_action_message_uses_requested_language(monkeypatch):
    monkeypatch.setattr(text_toolkit.wc, "OpenClipboard", lambda: None)
    monkeypatch.setattr(text_toolkit.wc, "CloseClipboard", lambda: None)
    # 其余格式读取和写入替换沿用现有测试夹具。
    ok, message = text_toolkit.merge_lines(language="en-US")
    assert ok is True
    assert message == "Merged into 1 line"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `py -3.12 -m pytest tests/test_action_i18n.py -q`

Expected: FAIL because action functions do not accept `language` and `PastePeekApp` has no language state.

- [ ] **Step 3: Write minimal implementation**

Route every user-visible message through `translate`, preserve default Chinese strings, pass `self._language` from `PastePeekApp.on_action_triggered`, and localize `_apply_binary_only_state` plus precondition failures. Keep clipboard locks, sequence checks, rollback and action keys unchanged.

- [ ] **Step 4: Run focused safety and action tests**

Run: `py -3.12 -m pytest tests/test_action_i18n.py tests/test_active_action_safety.py tests/test_action_sequence_safety.py tests/test_text_toolkit.py tests/test_text_toolkit_contract.py -q`

Expected: English message tests and all safety assertions pass.

- [ ] **Step 5: Commit**

```bash
git add src/manipulator/text_toolkit.py src/ui/app.py tests/test_action_i18n.py tests/test_text_toolkit.py tests/test_text_toolkit_contract.py
git commit -m "feat: 本地化主动操作反馈"
```

### Task 5: HUD 语言配置和即时刷新

**Files:**
- Modify: `src/ui/hud_window.py:133-1217`
- Modify: `tests/test_config.py`
- Modify: `tests/test_hud_preferences.py`
- Create: `tests/test_hud_i18n.py`

**Interfaces:**
- `HudWindow.language_changed = Signal(str)`。
- `HudWindow.set_language(language: str) -> str` updates static controls, saves config and emits only when the normalized language changes.
- `HudWindow.language() -> str` returns the current normalized language.
- `TargetIconBar.set_language(language: str) -> None` updates button labels, tooltips and menu labels.

- [ ] **Step 1: Write the failing tests**

```python
def test_config_defaults_to_chinese_and_persists_english(window, temp_config):
    assert hud_window.HudWindow._load_config()["language"] == "zh-CN"
    assert window.set_language("en-US") == "en-US"
    window._save_state()
    assert hud_window.HudWindow._load_config()["language"] == "en-US"


def test_hud_switch_refreshes_owned_labels(window, sample_output):
    window.update_result(sample_output)
    window.set_language("en-US")
    assert window._action_status.text() == "No action needed for this content"
    assert window._more_actions_btn.text() == "More actions"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `py -3.12 -m pytest tests/test_hud_i18n.py -q`

Expected: FAIL because config has no language field and HUD controls are hard-coded Chinese.

- [ ] **Step 3: Write minimal implementation**

Load and normalize `language` with the existing config defaults. Add `language_changed`, language state, language submenu in `TargetIconBar._show_more_menu`, and `_apply_language` for tooltips, action labels, first-run text, status, risk and error prefixes. On a language change, reconfigure the current output using the already localized `AppOutput` when supplied by `PastePeekApp`, without touching the clipboard.

- [ ] **Step 4: Run focused HUD/config tests**

Run: `py -3.12 -m pytest tests/test_hud_i18n.py tests/test_config.py tests/test_hud_preferences.py tests/test_hud_responsive_layout.py -q`

Expected: English HUD assertions and all existing geometry/config tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/ui/hud_window.py tests/test_hud_i18n.py tests/test_config.py tests/test_hud_preferences.py
git commit -m "feat: 增加 HUD 语言切换"
```

### Task 6: 托盘菜单与主流程接线

**Files:**
- Modify: `src/ui/tray_controller.py:1-164`
- Modify: `src/main.py:30-94`
- Modify: `tests/test_tray_lifecycle.py`
- Modify: `tests/test_tray_background_menu.py`
- Create: `tests/test_tray_i18n.py`

**Interfaces:**
- `TrayController.set_language(language: str) -> str` refreshes an existing menu without recreating signal connections.
- `HudWindow.language_changed` connects to both `PastePeekApp.set_language` and `TrayController.set_language` in `main`.

- [ ] **Step 1: Write the failing tests**

```python
def test_tray_language_switch_updates_menu(qapp):
    hud = HudWindow()
    controller = TrayController(hud, QIcon(), tray_available=True)
    controller.start()
    assert controller.set_language("en-US") == "en-US"
    menu = controller.findChild(QSystemTrayIcon).contextMenu()
    labels = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert "Exit PastePeek" in labels
    assert "启动 PastePeek" not in labels
    controller.stop()
    hud.close()
```

- [ ] **Step 2: Run tests to verify RED**

Run: `py -3.12 -m pytest tests/test_tray_i18n.py -q`

Expected: FAIL because `TrayController.set_language` and the language submenu do not exist.

- [ ] **Step 3: Write minimal implementation**

Store normalized language, keep references to all menu actions and language actions, update labels/check states in one refresh method, and localize startup error notifications. Connect HUD language changes to app/tray in `main.py`; initialize all three from the HUD-loaded config before monitoring starts.

- [ ] **Step 4: Run focused tray and lifecycle tests**

Run: `py -3.12 -m pytest tests/test_tray_i18n.py tests/test_tray_lifecycle.py tests/test_tray_background_menu.py tests/test_tray_fallback.py tests/test_tray_startup_error.py -q`

Expected: English menu tests and all existing tray lifecycle tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/ui/tray_controller.py src/main.py tests/test_tray_i18n.py tests/test_tray_lifecycle.py tests/test_tray_background_menu.py
git commit -m "feat: 本地化系统托盘菜单"
```

### Task 7: 全量验证、版本材料和发布候选

**Files:**
- Modify: `src/version.py`
- Modify: `README.md`, `README.en.md`, `CHANGELOG.md`, `CHANGELOG.en.md`
- Modify: `tests/test_version.py`, `tests/test_release_engineering.py`
- Modify: `checklist.md`, `改动日志.md`, `交接文档.md`

**Interfaces:**
- Version source, release docs and release tests remain synchronized; no existing `v2.0.0-rc.2` tag or artifact is overwritten.

- [ ] **Step 1: Write the failing release assertions**

```python
def test_next_release_mentions_runtime_language_switch():
    assert "语言切换" in Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert "language" in Path("README.en.md").read_text(encoding="utf-8").lower()
```

- [ ] **Step 2: Run the focused release test to verify RED**

Run: `py -3.12 -m pytest tests/test_release_engineering.py tests/test_version.py -q`

Expected: the new release assertion fails before release notes and version are updated.

- [ ] **Step 3: Write release updates**

Use the next version after `v2.0.0-rc.2` (for example `2.0.0-rc.3`) consistently in `src/version.py`, changelogs and tests. Document language choices, default Chinese behavior, English runtime coverage, and the existing unsigned-community-build and hardware-validation limits.

- [ ] **Step 4: Run all verification commands**

Run:

```powershell
py -3.12 -m run_tests -q
.venv\Scripts\ruff.exe check src tests scripts build.py run_tests.py generate_icon.py render_hud_asset.py
py -3.12 -m compileall -q src tests scripts build.py run_tests.py generate_icon.py render_hud_asset.py
```

Expected: zero test failures, Ruff clean, compileall exit code `0`. Rebuild and rerun the Windows GUI/tray acceptance scripts before calling the release candidate ready; remote GitHub Actions remains a separate gate.

- [ ] **Step 5: Commit**

```bash
git add src/version.py README.md README.en.md CHANGELOG.md CHANGELOG.en.md tests/test_version.py tests/test_release_engineering.py checklist.md 改动日志.md 交接文档.md
git commit -m "release: 发布 PastePeek v2.0.0-rc.3"
```
