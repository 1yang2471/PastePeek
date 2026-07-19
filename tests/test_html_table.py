"""HTML 表格转 Markdown 的回归测试。"""

from src.explainer.preview_renderer import HtmlToMarkdown


def test_table_without_header_does_not_duplicate_first_row():
    """无 th 表头时，首行既作为表头展示，也不能再次出现在数据区。"""
    markdown = HtmlToMarkdown().convert(
        "<table>"
        "<tr><td>A</td><td>B</td></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table>"
    )

    assert markdown.count("| A | B |") == 1
    assert "| 1 | 2 |" in markdown
