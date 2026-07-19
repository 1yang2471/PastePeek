"""UsageTracker 最小化日志结构测试。"""

import json

from src.usage.tracker import UsageTracker


def test_usage_log_only_contains_observable_fields(tmp_path):
    """没有产品入口的数据字段不应出现在本地日志中。"""
    tracker = UsageTracker(log_dir=tmp_path)
    tracker.on_update("code", "low")
    tracker.on_update("plain_text", "none")

    event = json.loads(
        (tmp_path / "usage.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert set(event) == {"ts", "content_type", "risk_level", "viewed"}
