"""PastePeek 命令行启动模式。"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class LaunchOptions:
    """应用启动模式与传给 Qt 的剩余参数。"""

    background: bool
    qt_arguments: list[str]


def parse_launch_options(arguments: Sequence[str]) -> LaunchOptions:
    """消费静默启动标记并保留其他 Qt 参数。"""
    qt_arguments = [argument for argument in arguments if argument != "--background"]
    return LaunchOptions(
        background="--background" in arguments,
        qt_arguments=qt_arguments,
    )
