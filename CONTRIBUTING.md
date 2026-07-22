# 参与贡献

[English](CONTRIBUTING.en.md) | 简体中文

感谢你帮助改进 PastePeek。项目聚焦于 Windows 上的粘贴结果预览，不计划加入剪贴板历史、云同步、AI 推理或插件系统。

参与讨论和提交改动时，请遵守 [社区行为准则](CODE_OF_CONDUCT.md)。

## 本地开发

需要 Windows 10/11、Python 3.12 和 Git。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-dev.txt
python run_tests.py
```

直接运行：

```powershell
python src\main.py
```

## 提交改动

- 新功能和缺陷修复先添加可观察行为测试，再实现最小改动。
- 新增注释和用户文档使用简体中文。
- 保持纯本地运行，不引入会上传剪贴板内容的依赖或服务。
- 不提交 `dist/`、`build/`、本地依赖目录或代理配置。

提交前运行：

```powershell
python run_tests.py
python -m compileall -q src tests
```

Pull Request 请说明用户问题、行为变化、验证方式和界面截图（涉及 HUD 时）。
