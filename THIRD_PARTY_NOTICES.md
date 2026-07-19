# PastePeek 第三方组件声明

PastePeek 自身代码使用 [MIT License](LICENSE)。Windows 发布包还包含下列第三方组件；这些组件继续适用各自的许可证，不因 PastePeek 的 MIT 许可证而改变。

## Qt for Python / Qt

| 组件 | 版本 | 许可证 |
|---|---:|---|
| PySide6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| PySide6 Addons | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| PySide6 Essentials | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| Shiboken6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| Qt 运行库 | 6.11.1 | 以各模块声明为准，PastePeek 使用 LGPL-3.0 路径分发 |

PastePeek 未修改上述库。PyInstaller 单文件程序运行时会把 Qt 动态库解压到临时目录并动态加载，不把 Qt 与 PastePeek 静态链接为单一作品。GNU LGPL 3.0 完整文本见 [licenses/LGPL-3.0.txt](licenses/LGPL-3.0.txt)。

用户有权为调试其对 LGPL 组件所做的修改而进行 reverse engineering。重新构建和替换组件所需信息如下：

- 安装与构建命令见 [README.md](README.md) 的“从源码运行”和“开发与构建”。
- 精确依赖及校验哈希见 `requirements.txt`。
- Qt 6.11.1 源码可从 [Qt Code Review](https://code.qt.io/cgit/) 或 [Qt 官方归档](https://download.qt.io/archive/qt/) 获取。
- Qt for Python 6.11.1 源码可从 [pyside/pyside-setup](https://code.qt.io/cgit/pyside/pyside-setup.git/) 获取。

Qt 与 Qt for Python 的版权归其各自贡献者及 The Qt Company 所有。这里的说明不构成对 Qt 商标的授权。

## Python 3.12

发布包包含 CPython 3.12 运行时，依据 Python Software Foundation License Version 2 分发。完整许可证文本见 `licenses/CPython-3.12-LICENSE.txt`；源码信息见 [Python 3.12 License](https://docs.python.org/3.12/license.html) 和 [CPython](https://github.com/python/cpython)。

## pywin32

pywin32 311 依据 PSF License 分发；本包随附的 `licenses/CPython-3.12-LICENSE.txt` 包含同一 PSF License Version 2 原文。项目与许可证信息见 [mhammond/pywin32](https://github.com/mhammond/pywin32)。

## PyInstaller

发布包包含 PyInstaller 6.20.0 bootloader。PyInstaller 使用 GPL-2.0-or-later，并附带允许分发所生成程序的特殊例外。许可证与例外全文见 `licenses/PyInstaller-COPYING.txt`，项目地址见 [pyinstaller/pyinstaller](https://github.com/pyinstaller/pyinstaller)。

## Lucide Icons

HUD 使用少量 Lucide 图标路径数据。Lucide 依据 ISC License 分发，版权归 Lucide Contributors 所有。许可证全文见 [licenses/Lucide-ISC.txt](licenses/Lucide-ISC.txt)，项目信息见 [lucide-icons/lucide](https://github.com/lucide-icons/lucide)。

## 构建期工具

pytest、Ruff、pip-audit 及其依赖只用于测试和质量检查，不随 PastePeek 运行包分发。精确版本见 `requirements-dev.txt`。

本文件仅用于满足许可证通知与归属要求，不替代各许可证原文。
