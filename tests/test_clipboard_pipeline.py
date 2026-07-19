"""剪贴板分析主流程的公开接口集成测试。"""

from src.clipboard.listener import ClipboardData
from src.ui.app import PastePeekApp


class StubClipboardListener:
    """返回固定剪贴板快照。"""

    def __init__(self, data: ClipboardData):
        self.data = data

    def read(self) -> ClipboardData:
        return self.data


class StubTargetDetector:
    """返回固定前台目标。"""

    def __init__(self, target: str):
        self.target = target

    def get_active_target(self) -> str:
        return self.target


def test_check_clipboard_emits_complete_analysis_for_new_snapshot():
    """一次公开检查应完成从快照到用户输出的完整分析。"""
    data = ClipboardData(
        text="标题\n第一项\n第二项",
        html="<h2>标题</h2><ul><li>第一项</li><li>第二项</li></ul>",
    )
    app = PastePeekApp(
        listener=StubClipboardListener(data),
        target_detector=StubTargetDetector("terminal"),
    )
    emitted = []
    app.analysis_ready.connect(emitted.append)

    output = app.check_clipboard()

    assert output is emitted[0]
    assert output.content_type == "rich_text"
    assert output.target == "terminal"
    assert output.deep_headings == 1
    assert output.deep_list_count == 1
    assert output.primary_action == "merge_lines"
    assert output.raw_text == data.text
    assert output.raw_html == data.html


def test_check_clipboard_emits_binary_only_snapshot_without_actions():
    """复制纯图片时必须替换旧预测，并禁止文本转换操作。"""
    data = ClipboardData(has_binary=True, has_image=True)
    app = PastePeekApp(
        listener=StubClipboardListener(data),
        target_detector=StubTargetDetector("word"),
    )
    emitted = []
    app.analysis_ready.connect(emitted.append)

    output = app.check_clipboard()

    assert output is emitted[0]
    assert output.has_binary is True
    assert output.content_type_label == "非文本"
    assert "图片、文件或音频" in output.prediction
    assert output.raw_text == ""
    assert output.raw_html == ""
    assert output.primary_action == ""
    assert output.available_actions == []


def test_binary_only_snapshot_can_switch_manual_target():
    '''非文本快照切换场景后仍应保持非文本说明和安全操作状态。'''
    data = ClipboardData(has_binary=True, has_image=True)
    app = PastePeekApp(
        listener=StubClipboardListener(data),
        target_detector=StubTargetDetector('word'),
    )
    emitted = []
    app.analysis_ready.connect(emitted.append)

    app.check_clipboard()
    app.set_manual_target('terminal')

    assert len(emitted) == 2
    switched = emitted[-1]
    assert switched.target == 'terminal'
    assert switched.has_binary is True
    assert switched.content_type_label == '非文本'
    assert '图片、文件或音频' in switched.prediction
    assert switched.primary_action == ''
    assert switched.available_actions == []


def test_binary_only_snapshot_description_covers_audio():
    '''标准音频剪贴板不得被错误描述成只有图片或文件。'''
    app = PastePeekApp(
        listener=StubClipboardListener(ClipboardData(has_binary=True)),
        target_detector=StubTargetDetector('word'),
    )

    output = app.check_clipboard()

    assert output is not None
    assert '音频' in output.prediction


def test_binary_only_snapshot_follows_automatic_target_changes():
    '''非文本快照也必须跟随前台窗口的自动目标变化。'''
    data = ClipboardData(has_binary=True, has_file=True)
    app = PastePeekApp(
        listener=StubClipboardListener(data),
        target_detector=StubTargetDetector('word'),
    )
    emitted = []
    app.analysis_ready.connect(emitted.append)

    app.check_clipboard()
    app._focus_monitor.target_changed.emit('terminal')

    assert len(emitted) == 2
    switched = emitted[-1]
    assert switched.target == 'terminal'
    assert switched.content_type_label == '非文本'
    assert switched.has_binary is True
    assert switched.available_actions == []


def test_transient_clipboard_read_failure_preserves_snapshot_identity():
    '''短暂读取失败后恢复同一内容时，不得重复发出分析结果。'''
    first = ClipboardData(text='保持不变')
    failure = ClipboardData()
    failure.read_succeeded = False
    snapshots = iter((first, failure, ClipboardData(text='保持不变')))

    class SequenceClipboardListener:
        def read(self):
            return next(snapshots)

    app = PastePeekApp(
        listener=SequenceClipboardListener(),
        target_detector=StubTargetDetector('word'),
    )
    emitted = []
    app.analysis_ready.connect(emitted.append)

    assert app.check_clipboard() is emitted[0]
    assert app.check_clipboard() is None
    assert app.check_clipboard() is None
    assert len(emitted) == 1
