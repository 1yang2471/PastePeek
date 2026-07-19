"""DeepAnalyzer — lightweight clipboard content metadata extractor.

Extracts structural features from clipboard HTML/content using only
the standard library (re + urllib.parse). Zero external dependencies.

What it extracts:
  - Format inventory: what clipboard formats are available
  - Structure: image count, table count, link count, heading count
  - Typography: font families, font sizes, bold/italic occurrences
  - URL detection: is_url, has_tracking_params (utm_source, fbclid, etc.)
  - Binary detection: has_binary, has_files flags
  - Dimensions: text length, HTML byte size, estimated visual complexity

Design: regex-based scanning as primary path (~0.2ms), urllib.parse for URL.
"""

import re
from dataclasses import dataclass, field

from src.url_policy import clean_url_text

# ── Regex patterns (compiled once) ──────────────────────────────────────
_RE_IMG   = re.compile(r"<\s*img\b", re.IGNORECASE)
_RE_TABLE = re.compile(r"<\s*table\b", re.IGNORECASE)
_RE_LINK  = re.compile(r"<\s*a\b", re.IGNORECASE)
_RE_UL    = re.compile(r"<\s*ul\b", re.IGNORECASE)
_RE_OL    = re.compile(r"<\s*ol\b", re.IGNORECASE)
_RE_H1_H6 = re.compile(r"<\s*h[1-6]\b", re.IGNORECASE)
_RE_BOLD  = re.compile(r"<\s*(?:b|strong)\b", re.IGNORECASE)
_RE_ITALIC = re.compile(r"<\s*(?:i|em)\b", re.IGNORECASE)
_RE_CODE  = re.compile(r"<\s*(?:code|pre)\b", re.IGNORECASE)
_RE_BLOCKQUOTE = re.compile(r"<\s*blockquote\b", re.IGNORECASE)

# Font extraction from inline style="font-family:...; font-size:..."
_RE_FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;\"']+)", re.IGNORECASE)
_RE_FONT_SIZE   = re.compile(r"font-size\s*:\s*([^;\"']+)", re.IGNORECASE)
_RE_COLOR       = re.compile(r"color\s*:\s*([^;\"']+)", re.IGNORECASE)


@dataclass
class DeepAnalysis:
    """Clipboard content metadata — extracted without heavy parsing.

    All counts are zero for plain text. Only populated when HTML is present.
    """

    # ── Format inventory ──
    has_html: bool = False
    has_rtf:  bool = False
    has_image: bool = False      # CF_DIB or similar
    has_file:  bool = False      # CF_HDROP
    has_audio: bool = False      # CF_WAVE or similar
    has_binary: bool = False     # any non-text binary format

    # ── Structural counts ──
    image_count:       int = 0
    table_count:       int = 0
    link_count:        int = 0
    list_count:        int = 0   # <ul> + <ol>
    heading_count:     int = 0
    blockquote_count:  int = 0
    code_block_count:  int = 0
    bold_count:        int = 0
    italic_count:      int = 0

    # ── Typography ──
    font_families: list[str] = field(default_factory=list)
    font_sizes:    list[str] = field(default_factory=list)
    colors_used:   list[str] = field(default_factory=list)


    # ── Dimensions ──
    text_length: int = 0          # plain text character count
    html_size:   int = 0          # raw HTML byte size
    complexity:  str = "low"      # "low" | "medium" | "high"

    # ── URL detection ──
    is_url: bool = False
    has_tracking_params: bool = False
    tracking_param_count: int = 0


class DeepAnalyzer:
    """Extract metadata from clipboard HTML/text content.

    Usage:
        analyzer = DeepAnalyzer()
        result = analyzer.analyze(html_string, plain_text)

    Performance: ~0.2–0.5ms for typical HTML (regex-only scan).
    """

    def analyze(self, html: str = "", text: str = "") -> DeepAnalysis:
        """Scan clipboard content and return structured metadata."""
        r = DeepAnalysis()

        r.text_length = len(text)
        r.has_html = bool(html)

        # ── URL detection (work on plain text, not HTML) ──
        _scan_url(text, r)

        if not html:
            # Plain text only — nothing structural to extract
            if "<" in text and ">" in text:
                # Text looks like HTML — classify as medium complexity
                r.complexity = "medium"
            return r

        r.html_size = len(html)

        # ── Structural counts ──
        r.image_count        = len(_RE_IMG.findall(html))
        r.table_count        = len(_RE_TABLE.findall(html))
        r.link_count         = len(_RE_LINK.findall(html))
        r.list_count         = len(_RE_UL.findall(html)) + len(_RE_OL.findall(html))
        r.heading_count      = len(_RE_H1_H6.findall(html))
        r.bold_count         = len(_RE_BOLD.findall(html))
        r.italic_count       = len(_RE_ITALIC.findall(html))
        r.code_block_count   = len(_RE_CODE.findall(html))
        r.blockquote_count   = len(_RE_BLOCKQUOTE.findall(html))

        # ── Typography (unique, deduplicated, capped at 10) ──
        r.font_families = _unique(_RE_FONT_FAMILY.findall(html), 10)
        r.font_sizes    = _unique(_RE_FONT_SIZE.findall(html), 10)
        r.colors_used   = _unique(_RE_COLOR.findall(html), 10)


        # ── Complexity ──
        score = (
            r.table_count * 3
            + r.image_count * 2
            + r.list_count * 2
            + r.heading_count
            + r.code_block_count
            + (1 if len(r.font_families) > 2 else 0)
            + (1 if len(r.colors_used) > 2 else 0)
        )
        if score >= 8:
            r.complexity = "high"
        elif score >= 3:
            r.complexity = "medium"
        else:
            r.complexity = "low"

        return r

    def analyze_clipboard_data(self, html: str, text: str) -> DeepAnalysis:
        """Alias for analyze() — used from app pipeline."""
        return self.analyze(html=html, text=text)


# ── Helpers ─────────────────────────────────────────────────────────────

def _scan_url(text: str, r: DeepAnalysis) -> None:
    """Check if text is a URL and whether it has tracking parameters."""
    _cleaned, removed, reason = clean_url_text(text)
    if reason == "not_url":
        return
    r.is_url = True
    r.tracking_param_count = len(removed)
    r.has_tracking_params = reason == "cleaned"


def _unique(items: list[str], cap: int = 10) -> list[str]:
    """Deduplicate while preserving order, return first `cap` items."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip().rstrip(";").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
            if len(result) >= cap:
                break
    return result
