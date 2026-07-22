# PastePeek v2.0.0-rc.2

[English](README.en.md) | 简体中文

[English changelog](CHANGELOG.en.md) | [中文变更日志](CHANGELOG.md)

英文公开文档已提供；当前运行时 HUD 和系统托盘文案仍为简体中文。

> 当前为最低预发布版（Pre-release）。已验证当前 Windows 单物理显示器环境；Windows 10、真实 per-monitor DPI、多物理显示器以及断电/强杀中的剪贴板写入结果尚未作兼容性承诺。

PastePeek 是一个面向 Windows 的轻量粘贴预览工具。复制内容后，它在桌面右下角显示内容类型、当前目标应用和粘贴风险；展开 HUD 后，可切换目标场景、查看近似粘贴效果，并按需净化链接、清洗格式或合并换行。

![PastePeek 300px 展开 HUD](assets/hud-expanded-300.png)

## 为什么需要它

同一份富文本、Markdown、代码或表格，粘贴到 Word、浏览器、终端和聊天应用时结果并不相同。PastePeek 在粘贴前给出具体结论，重点回答三件事：

- 目标应用会怎样处理当前内容；
- 哪些结构或格式可能丢失；
- 当前场景下最合适的处理动作是什么。

它不保存剪贴板历史，不上传内容，也不使用 AI 服务。

## 主要能力

- 识别富文本、纯文本、结构化文本和代码。
- 将标准、注册、未知图片/文件/音频格式及 HTML/RTF 内嵌媒体标记为非文本，并禁用破坏性文本转换。
- 通过前台进程名优先、窗口类名回退识别 8 类目标应用。
- 前台窗口事件钩子不可用时继续运行，复制内容时仍会读取当前前台目标。
- 提供 `4 × 8` 场景预测矩阵和四级风险提示。
- 为 Chrome、Markdown 编辑器、终端和代码编辑器生成近似效果预览。
- 为 Word、演示文稿、聊天应用和电子表格提供结构化风险清单。
- 仅对可确认安全的内容推荐净化链接、清洗格式或合并换行；代码、结构化、无正文或版本不可确认内容不提供主动操作。
- 支持自动目标检测、手动覆盖、方向键切换、位置记忆和多屏防遮挡。
- HTML 预览在本地净化，移除图片资源、脚本、样式、框架、对象和事件属性。
- 以便携单文件 EXE 运行，不需要安装。
- 支持系统托盘驻留、HUD 显隐和显式退出。
- 支持当前用户可选开机启动，登录时静默驻留托盘。

## 下载与运行

从仓库的 **Releases** 页面下载：

- `PastePeek.exe`
- `PastePeek.exe.sha256`

在 PowerShell 中校验：

```powershell
$expected = (Get-Content .\PastePeek.exe.sha256).Split()[0]
$actual = (Get-FileHash .\PastePeek.exe -Algorithm SHA256).Hash.ToLowerInvariant()
$expected -eq $actual
```

校验结果为 `True` 后双击 `PastePeek.exe`。程序不需要安装；重复启动只会唤醒已有实例，不会创建多个托盘图标或剪贴板监听器。Windows 10、真实 per-monitor DPI 和多物理显示器仍属于未验证环境。

当前社区构建未使用商业代码签名证书，Windows SmartScreen 可能显示“未知发布者”。请只从本仓库 Release 下载并先核对 SHA-256；哈希不一致时不要运行。

## 使用方式

1. 启动 PastePeek。
2. 在任意应用中复制文本、富文本、链接或代码。
3. 查看右下角 HUD 的内容类型、目标和风险色点。
4. 点击 HUD 展开预览，选择其他目标场景进行比较。
5. 仅在需要时点击主操作按钮修改剪贴板。

键盘操作仅在 HUD 获得焦点时生效：

| 按键 | 行为 |
|---|---|
| `←` / `→` | 在展开态切换目标场景 |
| `Enter` | 执行当前主操作 |
| `Escape` | 展开态折叠；常态最小化 |

“更多”菜单中的“自动检测”可清除手动目标覆盖。

## 系统托盘与开机启动

- 单击托盘图标可显示或隐藏 HUD。
- HUD 的“×”只隐藏界面，剪贴板监听继续运行。
- 右键托盘图标并选择“退出 PastePeek”才会完整结束应用。
- 托盘菜单中的“开机启动”只对便携 EXE 可用，源码运行不会注册 Python 命令。
- 启用后写入当前用户的 Windows `Run` 注册值，不需要管理员权限；登录时使用 `--background` 静默驻留托盘。
- 保存位置和从托盘恢复后的窗口都会按当前屏幕可用工作区四边校正，避免被顶部、底部或侧边任务栏遮挡。
- 如果移动了 EXE，旧路径不会显示为已启用；在新位置重新勾选即可更新路径。

系统托盘不可用时，HUD 的“×”会直接退出，避免留下无法关闭的后台进程。

## 支持的目标

| 目标 | 常见应用 | 预览方式 |
|---|---|---|
| Word | Microsoft Word、WPS Writer | 结构与格式清单 |
| Chrome | Chrome、Edge | 净化后的本地 HTML |
| 代码编辑器 | VS Code、Cursor | 等宽纯文本 |
| 终端 | Windows Terminal、PowerShell、cmd | 保留换行的纯文本 |
| 聊天应用 | 微信、Teams、Slack、Discord | 简化文本与风险清单 |
| Markdown | Typora、Obsidian | HTML 转 Markdown |
| 电子表格 | Excel、WPS Spreadsheets | 行列结构清单 |
| 演示文稿 | PowerPoint、WPS Presentation | 大纲与格式清单 |

目标识别是启发式判断。未识别窗口会使用配置中的 `default_target`，用户也可以在 HUD 中手动选择。

## 隐私与本地数据

PastePeek 的运行路径不需要网络：

- 剪贴板内容只在当前进程内分析；
- 不保存原始剪贴板内容；
- 不自动修改剪贴板，只有用户触发操作时才写回；
- HTML 预览不会加载远程或本地资源；
- UsageTracker 默认关闭；用户显式开启后只记录时间、内容类型、风险等级和是否查看 HUD。

本地文件位于 `%LOCALAPPDATA%\PastePeek\`：

- `config.json`：位置和界面偏好；
- `usage.jsonl`：可选的匿名本地使用记录，单文件默认最多约 1 MiB，超限时覆盖旧批次。

将 `usage_tracking_enabled` 设为 `true` 才会开启记录，设为 `false` 可关闭；也可以直接删除 `usage.jsonl`。安全问题请参阅 [SECURITY.md](SECURITY.md)。

只有用户主动启用开机启动时，系统才会在 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 下写入名为 `PastePeek` 的当前 EXE 启动命令；禁用后只删除该值。

## 从源码运行

需要 Windows 10/11 和 Python 3.12：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.txt
python src\main.py
```

## 开发与构建

```powershell
python -m pip install --require-hashes -r requirements-dev.txt
python run_tests.py
pip-compile --allow-unsafe --generate-hashes --no-emit-index-url --output-file=requirements-dev.txt --strip-extras requirements-dev.in
python -m ruff check src tests scripts build.py run_tests.py generate_icon.py render_hud_asset.py
python -m compileall -q src tests scripts build.py run_tests.py generate_icon.py render_hud_asset.py
python render_hud_asset.py
python build.py
powershell -ExecutionPolicy Bypass -File scripts/smoke_windows.ps1
powershell -ExecutionPolicy Bypass -File scripts/smoke_tray_windows.ps1
python scripts/accept_actions_windows.py
python scripts/accept_gui_windows.py
python scripts/accept_tray_windows.py
```

构建会生成：

```text
dist/PastePeek.exe
dist/PastePeek.exe.sha256
dist/PastePeek-<version>-win64.zip
```

EXE 会写入与 `src/version.py` 一致的 Windows 文件/产品版本、产品名、文件说明、社区署名和版权。

CI 在 Windows + Python 3.12 上运行静态检查、测试、编译、依赖审计和完整构建；推送 `v*` 标签时，Release 工作流会重新验证并创建 Pre-release，上传独立 EXE、SHA-256、包含完整许可证材料的 ZIP 和许可证文件。当前构建未使用代码签名证书，Windows SmartScreen 可能显示未知发布者。

## 项目结构

```text
src/
├── clipboard/     剪贴板读取
├── analyzer/      内容与结构分析
├── detector/      前台目标识别
├── explainer/     场景预测与安全预览
├── manipulator/   用户触发的剪贴板操作
├── listener/      前台窗口变化监听
├── ui/            HUD 与应用控制器
├── usage/         可选本地统计
├── models/        公共数据结构
├── launch_options.py  手动/登录启动模式
├── single_instance.py 单实例与唤醒通信
├── startup.py        当前用户开机启动管理
├── main.py           应用入口
└── version.py        唯一版本来源
scripts/
├── accept_actions_windows.py 三项主动操作的真实剪贴板保真验收
├── accept_gui_windows.py  源码版与 EXE 的完整 GUI/剪贴板验收
└── accept_tray_windows.py 后台启动与托盘生命周期 UIA 验收
render_hud_asset.py  README 截图生成与字体验收
```

## 项目边界

PastePeek 当前不提供剪贴板历史、云同步、跨设备、AI 推理、插件系统或内容编辑器。场景预览是近似结果，不替代目标应用自身的粘贴实现；复杂 Office 排版、嵌套表格和应用私有剪贴板格式仍需在目标应用中确认。

贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，使用支持见 [SUPPORT.md](SUPPORT.md)，社区协作遵循 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。项目采用 [MIT License](LICENSE)。
