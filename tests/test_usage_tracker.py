"""UsageTracker v2.0 本地日志契约测试。"""

import json

from src.usage.tracker import UsageTracker


def test_usage_log_contains_no_removed_source_type(tmp_path):
    """v2 日志不得继续输出已移除的来源类型字段。"""
    tracker = UsageTracker(log_dir=tmp_path)
    tracker.on_update("rich_text", "medium")
    tracker.on_viewed()
    tracker.on_update("plain_text", "none")

    first_event = json.loads(
        (tmp_path / "usage.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert "source_type" not in first_event
    assert first_event["content_type"] == "rich_text"
    assert first_event["risk_level"] == "medium"
    assert first_event["viewed"] is True


def test_close_flushes_last_pending_session(tmp_path):
    '''应用关闭时必须写出最后一个尚未被后续更新触发的会话。'''
    tracker = UsageTracker(log_dir=tmp_path)
    tracker.on_update('plain_text', 'none')
    tracker.on_viewed()

    tracker.close()

    event = json.loads(
        (tmp_path / 'usage.jsonl').read_text(encoding='utf-8').splitlines()[0]
    )
    assert event['content_type'] == 'plain_text'
    assert event['viewed'] is True


def test_usage_log_is_bounded_by_configured_limit(tmp_path):
    """本地统计日志超过上限时应丢弃旧批次而不是无限增长。"""
    tracker = UsageTracker(log_dir=tmp_path, max_bytes=256)
    for _ in range(20):
        tracker.on_update("plain_text", "none")
    tracker.close()

    log_path = tmp_path / "usage.jsonl"
    assert log_path.stat().st_size <= 256
    assert log_path.read_text(encoding="utf-8").strip()
