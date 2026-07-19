"""PastePeek 启动模式解析测试。"""

from src.launch_options import parse_launch_options


def test_background_option_is_consumed_before_qt_starts():
    """登录启动标记应被识别，其他 Qt 参数必须保留。"""
    options = parse_launch_options(
        ["PastePeek.exe", "--background", "-platform", "offscreen"]
    )

    assert options.background
    assert options.qt_arguments == ["PastePeek.exe", "-platform", "offscreen"]
