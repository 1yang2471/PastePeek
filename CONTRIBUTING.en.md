# Contributing

[简体中文](CONTRIBUTING.md) | English

Thank you for helping improve PastePeek. The project focuses on previewing paste results on Windows and does not plan to add clipboard history, cloud sync, AI inference, or a plugin system.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.en.md) in discussions and contributions.

## Local Development

Windows 10/11, Python 3.12, and Git are required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-dev.txt
python run_tests.py
```

Run from source:

```powershell
python src\main.py
```

## Submitting Changes

- Add an observable behavior test before implementing a new feature or bug fix.
- Keep the local-only, no-history, no-cloud product boundary intact.
- Do not add dependencies or services that upload clipboard content.
- Do not commit `dist/`, `build/`, local dependency directories, proxy configuration, clipboard text, or private development records.

Run these checks before opening a Pull Request:

```powershell
python run_tests.py
python -m compileall -q src tests
```

Describe the user problem, behavior change, verification method, and sanitized UI screenshots when the HUD is involved.

For Chinese contribution guidance, see [CONTRIBUTING.md](CONTRIBUTING.md).
