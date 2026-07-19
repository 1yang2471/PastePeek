"""在不修改系统设置的前提下验收 Qt 多缩放因子。"""

from __future__ import annotations

import json
import os
import sys

from accept_gui_windows import (
    RESULTS_DIR,
    ROOT,
    backup_clipboard,
    restore_clipboard,
    run_scenario,
)

SCALE_FACTORS = {
    "125": "1.25",
    "150": "1.5",
    "200": "2.0",
}


def main() -> None:
    """逐个缩放因子验收源码版和最终 EXE。"""
    previous_scale = os.environ.get("QT_SCALE_FACTOR")
    clipboard_backup = backup_clipboard()
    results: dict[str, object] = {
        "kind": "process-local Qt scale acceptance",
    }
    try:
        for label, factor in SCALE_FACTORS.items():
            os.environ["QT_SCALE_FACTOR"] = factor
            results[label] = {
                "factor": factor,
                "source": run_scenario(
                    f"dpi-{label}-source",
                    [sys.executable, str(ROOT / "src" / "main.py")],
                    check_auto=False,
                    geometry_scale=float(factor),
                ),
                "exe": run_scenario(
                    f"dpi-{label}-exe",
                    [str(ROOT / "dist" / "PastePeek.exe")],
                    check_auto=False,
                    geometry_scale=float(factor),
                ),
            }
        results["passed"] = True
    finally:
        if previous_scale is None:
            os.environ.pop("QT_SCALE_FACTOR", None)
        else:
            os.environ["QT_SCALE_FACTOR"] = previous_scale
        restore_clipboard(clipboard_backup)
        results["clipboard_restored"] = True
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "dpi-results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
