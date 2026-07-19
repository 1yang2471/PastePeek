"""主动操作前的代码与结构化内容安全分类。"""

import csv
import io
import re

_CODE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for pattern in (
        r"^\s*(?:public|private|protected|internal|static|final|abstract|sealed)+\s+(?:class|interface|enum|record)\b",
        r"^\s*(?:(?:public|private|protected|static|final)\s+)*(?:void|int|string|bool|char|float|double)\s+\w+\s*\(",
        r"^\s*(?:for|while|until|if|case)\b.*(?:;\s*(?:do|then)|\s+(?:do|then))\s*$",
        r"^\s*\$[\w:.-]+\s*=",
        r"\|\s*[A-Z][\w-]+\s*(?:\{|$)",
        r"^\s*(?:FROM|RUN|COPY|ADD|CMD|ENTRYPOINT|WORKDIR|ENV|ARG|EXPOSE|VOLUME|USER|LABEL)\b",
        r"^\s*(?:resource|module|provider|variable|output|data|locals|terraform)\s+",
        r"^\s*(?:fun|function|local\s+function)\s+\w+\s*\(",
        r"^\s*#!",
        r"\\\s*$",
        r"^\s*[.#@]?[A-Za-z][\w.#: >+~,*-]*\s*\{\s*$",
    )
)


def _looks_like_table(text: str) -> bool:
    """用标准 CSV 解析器识别列结构，避免合并破坏表格。"""
    for delimiter in (",", "\t", "|"):
        try:
            rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
        except csv.Error:
            continue
        rows = [row for row in rows if any(cell.strip() for cell in row)]
        if len(rows) < 2:
            continue
        widths = {len(row) for row in rows}
        if len(widths) == 1 and next(iter(widths), 0) > 1:
            return True
    return False


def detect_protected_content_type(
    text: str,
    html: str | None = None,
) -> str | None:
    """返回 `code` 或 `structured_text`；普通文本返回 `None`。"""
    if html and re.search(r"<\s*(?:pre|code)\b", html, re.IGNORECASE):
        return "code"

    if any(pattern.search(text) for pattern in _CODE_PATTERNS):
        return "code"

    if html and html.strip():
        return None

    assignment_lines = re.findall(
        r"(?m)^\s*(?:export\s+)?[A-Za-z_][\w.-]*\s*=\s*\S+",
        text,
    )
    if len(assignment_lines) >= 2:
        return "structured_text"

    if re.search(
        r"(?m)^\s*#(?:define|include|if|ifdef|ifndef|elif|else|endif|pragma|undef)\b",
        text,
    ):
        return "code"

    if re.search(r"(?m)^(?:diff --git\s+\S|---\s+\S|\+\+\+\s+\S|@@\s+)", text):
        return "structured_text"

    if len(re.findall(r"(?m)^\s*\d+[.)]\s+\S", text)) >= 2:
        return "structured_text"

    if re.search(r"(?m)^\s*[\w.-]+:\s*\r?\n\t\S", text):
        return "code"

    if re.search(r"(?m)\.each\s+do\b|^\s*local\s+\w+\s*=", text):
        return "code"

    if re.search(r"(?mi)^\s*@?echo\s+off\s*$|^\s*set\s+\w+=", text):
        return "code"

    stripped = text.strip()
    if (
        (stripped.startswith("{") and stripped.endswith("}"))
        or (stripped.startswith("[") and stripped.endswith("]"))
        or re.search(r"(?m)^\s*\[[^\]\r\n]+\]\s*$", text)
        or len(re.findall(r"(?m)^\s*[\w.-]+\s*:\s*", text)) >= 2
        or re.search(r"(?m)^\s*#{1,6}\s+\S", text)
        or len(re.findall(r"(?m)^\s*[-*]\s+\S", text)) >= 2
        or _looks_like_table(text)
        or (
            stripped.startswith("<")
            and stripped.endswith(">")
            and re.search(r"</?[A-Za-z][\w:.-]*\b", stripped)
        )
    ):
        return "structured_text"

    return None
