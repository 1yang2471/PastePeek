# Changelog

## v2.0.0-rc.2（预发布，2026-07-20）

- 更新应用图标为剪贴板、预览之眼和风险提示组合，覆盖 16–256px 多尺寸透明 ICO，适配托盘、窗口标题栏和 EXE 资源管理器视图。
- 新增图标发行资产契约测试，确保各尺寸、透明通道和 16px 托盘可见性稳定。

## v2.0.0-rc.1（预发布，2026-07-20）

- 主动操作按“未知即拒绝”加固：签名/鉴权 URL、歧义查询、代码/结构化内容、标准/注册/未知非文本格式和 HTML/RTF 内嵌媒体均失败关闭。
- HUD 更新为低干扰浅色系统工具风：加入风险文字标签、Lucide 类别与操作图标、青绿色主操作、无操作状态文字、持久错误反馈和 300/400/640px 响应式目标栏。
- 预览区按实际渲染内容调整高度，短内容不保留大段空白，结构化预览不再被隐藏滚动区裁切；展开窗口保留 16px 工作区安全边距。
- 当前候选完成 `753` 项自动化回归；真实三项剪贴板、源码版/EXE GUI、Edge/WPS/微信回贴和托盘 UIA 验收均通过，`clipboard_restored=true`。
- 100% DPI 单显示器实机通过；Qt 进程级 125%、150%、200% 的源码版与 EXE GUI/剪贴板流程通过。真实 per-monitor DPI 与多物理显示器仍待外部环境验收。
- 前台窗口钩子注册失败时降级运行，不再让无控制台 EXE 静默退出；复制内容时仍会读取当前前台目标。
- HUD 可恢复左侧或上方副屏的合法负坐标，按可用工作区四边避开任意方向的任务栏，并为高 DPI 原生外框取整保留额外安全量。
- Windows EXE 现在包含文件/产品版本和产品身份；Release 按唯一版本源精确选择 ZIP，测试入口不再回退到本地 vendored 目录。
- 后台启动且默认展开的 HUD 从托盘首次显示后会重新执行防遮挡，修复隐藏初始化时无原生窗口句柄造成的越界。
- Release checkout 不再持久化具有写权限的凭据，发布令牌仅通过最终 `gh release create` 步骤的 `GH_TOKEN` 使用。
- EXE 校验值以 GitHub Release 附带的 `.sha256` 文件为准；当前版本作为最低公开预发布版，不代表稳定版兼容性承诺。
- 最低预发布版安全修复：非法或越界端口 URL 不再净化；存在无法完整回滚的注册剪贴板格式时三项主动操作失败关闭。
- 发布 ZIP 现在包含项目 MIT、CPython、PyInstaller、LGPL 和 Lucide 许可证原文；Release 使用动态版本文件名、固定 Action 提交并创建 Pre-release。
- UsageTracker 改为默认关闭，日志默认限制为约 1 MiB。
- 首次公开版本改为 `v2.0.0-rc.1`；开发与构建依赖使用 SHA-256 锁定，并补齐 GitHub Issue、Pull Request、支持和行为准则入口。
- GUI 验收在真实鼠标不可用且 Windows 明确返回 `SetCursorPos` 错误时回退到 UIA 控件调用，并在结果中记录实际输入模式；其他输入错误仍直接失败。
- GUI 边界断言会等待原生 EXE 完成短暂的异步重定位，持续越界仍失败；源码版与 EXE 随后均以物理鼠标完成完整流程。

## 2.0.0 开发基线 — Scenario-Based Paste Preview (2026-07-15)

### New Features

- **Scenario-Based Paste Preview**: Render an approximation of how clipboard content will look when pasted into the selected target application. High-fidelity targets (Chrome, Markdown editor, Terminal, Code editor) get rendered previews; low-fidelity targets (Word, Presentation, Chat app, Spreadsheet) show structured summaries with risk items.
- **Horizontal Target Icon Bar**: Replaces the dropdown selector with a compact horizontal icon bar in the expanded HUD. Commonly used targets are always visible; the rest are accessible via a "More" dropdown.
- **Keyboard Navigation**: Use `←` / `→` to cycle through target scenarios when the HUD is focused, and press `Enter` to trigger the primary action for the selected target.
- **Extended Configuration**: `config.json` now persists `last_target`, `default_expand`, `default_target`, `ui_width`, and `usage_tracking_enabled`.
- **Portable Tray Lifecycle**: 便携 EXE 现在驻留系统托盘，支持 HUD 显隐、显式退出和托盘不可用时的安全回退。
- **Single Instance Activation**: 同一用户会话只保留一个监听实例，重复手动启动会唤醒已有 HUD。
- **Optional Startup**: 托盘菜单可管理当前用户开机启动，登录时使用 `--background` 静默驻留。

### Changes

- **Simplified Interaction Model**: Reduced the HUD from a 7-layer progressive reveal to a 2-layer model — a compact idle summary and a single expanded preview panel.
- **Target-Aware Smart Actions**: The primary action button is now recommended per `(content_type, target)` instead of being globally determined. Less relevant actions are moved to a "More Actions" menu.
- **Foreground Target Detection**: Process names now disambiguate Chromium and Electron applications before window-class fallback, covering Chrome, Edge, VS Code, Cursor, Windows Terminal, Office, WPS, major chat apps, Typora, and Obsidian.
- **Minimal Usage Schema**: Local usage records now contain only timestamp, content type, risk level, and whether the HUD was viewed.

### Security and Reliability

- Sanitized browser previews with a standard-library HTML parser. Images become local placeholders; scripts, styles, frames, objects, resource declarations, event attributes, and CSS URLs are removed.
- Preserved paragraphs, line breaks, lists, and table boundaries when rich text falls back to plain text.
- Corrected rich-text predictions for terminals, code editors, and Markdown editors to match Windows clipboard format negotiation.
- Fixed target-bar overflow at the 300 px minimum width and fixed expanded HUD minimization retaining a very tall content height.
- Fixed standard Windows `CF_WAVE` audio clipboard detection, which previously queried an unrelated registered format.
- Preserved non-text state when users switch targets manually or through foreground-window detection, including accurate image, file, and audio messaging.
- Preserved the last successful snapshot across transient clipboard-open failures, preventing duplicate HUD updates when the same content becomes readable again.
- Prevented target-only prediction changes from splitting one clipboard item into multiple local usage sessions.
- Flushed the final pending usage session during normal application shutdown.
- Added a reproducible README HUD renderer with explicit CJK font registration, glyph validation, pixel checks, and a visually verified 300 px asset.
- Added a controlled Windows smoke script that validates source and one-file EXE startup while cleaning both PyInstaller launcher and child processes.
- 开机启动只接受冻结 EXE，使用带引号的当前路径；路径移动、注册表拒绝访问和写入失败均保持诚实状态。
- 单实例通信使用用户会话锁和真实第二进程激活验证，正常退出后立即释放所有权。
- 后台启动遇到系统托盘不可用时改为显示 HUD，避免进程在用户无入口时静默驻留。
- 后台启动时托盘菜单会正确显示“显示 PastePeek”，菜单打开前也会刷新当前开机启动真实状态。
- 单实例通信为正在初始化 HUD 与托盘的主实例保留 2 秒响应窗口，避免重复手动启动过早失败。
- 完整 GUI 与托盘 UIA 验收脚本已纳入 `scripts/`，依赖由开发锁文件管理，剪贴板备份只保存在内存中。
- 移除被忽略的 `vendor_pkgs*` 依赖回退及旧测试引用，源码、测试和构建统一使用声明依赖。
- 升级 Pillow 与 pytest 的安全修复版本，并将 pip-tools 纳入可复现开发工具链。
- Removed unused `ui_height` and transient `expanded` configuration fields; clamped `ui_width` to 300–640 px.
- Added a single version source, separated runtime/development dependencies, Windows CI, tag-based release automation, and SHA-256 build artifacts.

### Removed

- **Sensitive Information Detection & Masking**: Removed phone number, email, and ID card scanning, along with the mask-sensitive action, UI warnings, and related tests.
- **Source Type Inference**: Removed `source_type` detection (Word/PDF/Markdown/web/AI/plain). Predictions now rely solely on `content_type × target`.

## v1.1.0 — Polish & Privacy Release (2026-07-01)

### New Features

- **Smart Sensitive Data Masking**: Detects phone numbers, email addresses, and ID card numbers in clipboard text; one-click mask replaces them with privacy-safe placeholders.
- **First-Run Guidance**: Yellow tip banner in HUD showing drag hint and Space shortcut; auto-dismisses on drag or close.
- **Multi-Screen Positioning**: Saved HUD coordinates are validated against all connected screens; resets to primary screen if the previous monitor was disconnected.
- **Expand Anti-Occlusion**: When expanding the HUD, it automatically shifts upward if the bottom would exceed the available screen area.
- **Action Feedback**: Green success flash and red error flash (500ms) on clipboard operations; errors show user-friendly messages instead of Windows error codes.
- **Preview Character Count**: Preview snippets now show `(共 N 字)` so users know the exact length of transformed text.

### Improvements

- Unified exception handling with `ClipboardBusyError` and `EmptyContentError` across all clipboard operations.
- `mask_sensitive` clipboard read/write logic moved into `text_toolkit` for consistency and testability.
- Fixed `on_action_triggered()` to catch `ClipboardBusyError` and `EmptyContentError` so errors are shown in the HUD instead of silently failing in the Qt event loop.
- Removed 6 legacy modules and 3 obsolete test files no longer used by the main pipeline.
- Test suite updated: 99 tests passing.

## v1.0.0 — Initial Release (2026-06-29)

### Core Features

- **Content Type Detection**: Automatically classifies clipboard content into 4 types:
  - Rich Text (web pages, AI responses, Word exports)
  - Plain Text (chat inputs, search boxes)
  - Structured Text (Markdown documents)
  - Code (IDE content, scripts)

- **Risk Prediction**: One-click risk assessment for Word paste:
  - Medium risk: Rich text content may have format changes
  - Low risk: Structured / code content may have indentation changes
  - No risk: Plain text works everywhere

- **Suggestion System**: Lightweight rule-based suggestion for each content type:
  - Rich text → use Ctrl+Shift+V (paste as plain text)
  - Code → Ctrl+Shift+V to preserve indentation
  - Plain text → paste directly

- **3-Line Minimal UI**: System tray popup with:
  - Line 1: Risk conclusion (icon + label)
  - Line 2: One-sentence reason
  - Line 3: Actionable suggestion
  - Optional expand for content type details

- **System Tray Integration**: Sits in the Windows system tray, auto-detects clipboard changes, popup auto-hides after 5 seconds.

### Technical

- Python 3.11+, PySide6 GUI framework
- Built-in `html.parser` (zero external HTML parsing dependency)
- `win32clipboard` for clipboard access
- 29 automated tests, all passing
- Single-file PyInstaller build for Windows 10/11

### Design Principles

- Prediction based on content type, not target application
- No AI, no rule engine — pure static text mapping
- No clipboard history, no content editing, no auto-fix
- Privacy-first: 100% local, no network, no data collection
