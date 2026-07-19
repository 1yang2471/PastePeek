"""UsageTracker — zero-interaction real-usage feedback logger.

Logs one JSONL line per clipboard session to %LOCALAPPDATA%/PastePeek/usage.jsonl.

Fields:
  ts           — ISO 8601 timestamp
  content_type — rich_text / plain_text / structured_text / code
  risk_level   — none / low / medium / high
  viewed       — true if user ever hovered the HUD during this session

Design: zero UI impact, zero interaction burden.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_MAX_BYTES = 1024 * 1024


def _log_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    p = Path(local_appdata) / "PastePeek"
    p.mkdir(parents=True, exist_ok=True)
    return p


class UsageTracker:
    """Passively track clipboard sessions for real-usage evaluation.

    Usage:
      tracker = UsageTracker()
      tracker.on_update(content_type, risk_level)               # on clipboard change
      tracker.on_viewed()                                        # on HUD hover
    """

    def __init__(self, log_dir: Path | None = None, max_bytes: int = DEFAULT_MAX_BYTES):
        self._log_path = (log_dir or _log_dir()) / "usage.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._max_bytes = max(256, int(max_bytes))
        except (TypeError, ValueError):
            self._max_bytes = DEFAULT_MAX_BYTES
        self._pending: dict | None = None
        self._viewed = False

    # ── Public API ──────────────────────────────────────────────────

    def on_update(self, content_type: str, risk_level: str):
        """New clipboard content arrived. Log previous session, start new."""
        self._flush()
        self._pending = {
            "ts": datetime.now(UTC).isoformat(),
            "content_type": content_type,
            "risk_level": risk_level,
            "viewed": False,
        }
        self._viewed = False

    def on_viewed(self):
        """User hovered the HUD (implying they looked at the prediction)."""
        self._viewed = True
        if self._pending:
            self._pending["viewed"] = True

    def close(self):
        '''写出最后一个待处理会话；可安全重复调用。'''
        self._flush()

    # ── Internal ────────────────────────────────────────────────────

    def _flush(self):
        if self._pending is None:
            return
        try:
            payload = json.dumps(self._pending, ensure_ascii=False) + "\n"
            payload_size = len(payload.encode("utf-8"))
            current_size = self._log_path.stat().st_size if self._log_path.exists() else 0
            mode = "w" if current_size + payload_size > self._max_bytes else "a"
            with open(self._log_path, mode, encoding="utf-8") as f:
                f.write(payload)
        except OSError:
            pass  # never crash on logging failure
        self._pending = None
