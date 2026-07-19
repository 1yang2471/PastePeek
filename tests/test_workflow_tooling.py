'''维护工具的远端质量门禁契约。'''

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_workflows_lint_hud_asset_generator():
    '''CI 与发布流程都必须静态检查 README 截图生成器。'''
    for filename in ('ci.yml', 'release.yml'):
        workflow = (
            ROOT / '.github' / 'workflows' / filename
        ).read_text(encoding='utf-8')

        assert 'ruff check' in workflow
        assert 'render_hud_asset.py' in workflow


def test_gui_acceptance_uses_versioned_script_and_declared_dependency():
    '''完整 GUI 验收不得依赖被忽略的本地依赖目录。'''
    for filename in ('accept_gui_windows.py', 'accept_tray_windows.py'):
        script_path = ROOT / 'scripts' / filename

        assert script_path.exists()
        script = script_path.read_text(encoding='utf-8')
        assert 'ui_test_deps' not in script

    development = (
        ROOT / 'requirements-dev.in'
    ).read_text(encoding='utf-8').splitlines()

    assert 'pywinauto==0.6.9' in development
    assert 'Pillow==12.3.0' in development


def test_source_smoke_prefers_project_virtual_environment():
    """源码冒烟应优先使用已安装依赖的项目虚拟环境。"""
    script = (ROOT / "scripts" / "smoke_windows.ps1").read_text(
        encoding="utf-8"
    )

    assert ".venv\\Scripts\\python.exe" in script


def test_test_runner_uses_current_environment_without_vendored_fallback():
    """测试入口必须使用当前 Python 环境中声明安装的依赖。"""
    runner = (ROOT / "run_tests.py").read_text(encoding="utf-8")

    assert "vendor_pkgs" not in runner
    assert "sys.path.insert" not in runner
    assert "[sys.executable, \"-m\", \"pytest\"" in runner
