"""README HUD 截图生成命令的集成测试。"""

import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]


def test_render_hud_asset_command_creates_expanded_300px_png(tmp_path):
    """维护者应能通过仓库命令生成可用的真实 HUD 截图。"""
    output = tmp_path / "hud-expanded-300.png"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "render_hud_asset.py"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "rendered=" in result.stdout
    assert 'cjk_supported=true' in result.stdout
    assert output.is_file()

    image = QImage(str(output))
    assert not image.isNull()
    assert image.width() == 300
    assert image.height() > 200


def test_render_hud_asset_command_supports_responsive_review_width(tmp_path):
    """维护者应能直接渲染宽版 HUD 进行响应式视觉复核。"""
    output = tmp_path / "hud-expanded-400.png"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "render_hud_asset.py"),
            "--output",
            str(output),
            "--width",
            "400",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    image = QImage(str(output))
    assert not image.isNull()
    assert image.width() == 400
