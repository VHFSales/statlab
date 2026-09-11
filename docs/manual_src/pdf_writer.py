"""Minimal, dependency-free PDF writer (pure Python stdlib).

Enough to produce a clean multi-page text manual: title/heading/body/bullet styles,
automatic word-wrapping, and pagination. Uses the standard Helvetica fonts, so no
font embedding is needed. Text is encoded latin-1 (covers Portuguese accents).

This is intentionally small and self-contained so the manual can be generated in any
environment (including offline sandboxes without matplotlib/reportlab).
"""

from __future__ import annotations

import zlib
from typing import List, Tuple

# Page geometry (US Letter, points).
PAGE_W, PAGE_H = 612.0, 792.0
MARGIN_L, MARGIN_R = 64.0, 64.0
MARGIN_T, MARGIN_B = 72.0, 64.0
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

# Approximate Helvetica character widths (in 1/1000 em) for common characters.
# We use a single average width per font to keep wrapping simple but reliable.
AVG_WIDTH_FACTOR = 0.52       # Helvetica average glyph width as a fraction of size
AVG_WIDTH_FACTOR_BOLD = 0.56


# Map common Unicode punctuation to WinAnsiEncoding byte values (single-byte).
_WINANSI = {
    "\u2022": "\x95",  # bullet
    "\u2014": "\x97",  # em dash
    "\u2013": "\x96",  # en dash
    "\u2018": "\x91", "\u2019": "\x92",  # curly single quotes
    "\u201c": "\x93", "\u201d": "\x94",  # curly double quotes
    "\u2026": "\x85",  # ellipsis
}


def _to_winansi(text: str) -> str:
    for uni, byte in _WINANSI.items():
        text = text.replace(uni, byte)
    return text


def _esc(text: str) -> str:
    """Escape a string for a PDF text-showing operator (WinAnsiEncoding)."""
    text = _to_winansi(text)
    return (text.replace("\\", r"\\")
                .replace("(", r"\(")
                .replace(")", r"\)"))


def _text_width(text: str, size: float, bold: bool) -> float:
    factor = AVG_WIDTH_FACTOR_BOLD if bold else AVG_WIDTH_FACTOR
    return len(text) * size * factor


def _wrap(text: str, size: float, bold: bool, max_w: float) -> List[str]:
    """Greedy word-wrap to fit max_w points."""
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if _text_width(trial, size, bold) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


class Block:
    """A styled block of text to render."""
    def __init__(self, text: str, style: str):
        self.text = text
        self.style = style  # title | h1 | h2 | body | bullet | small | spacer


# style -> (font, size, bold, leading, space_before, indent, color)
STYLES = {
    "title":  ("F2", 22, True, 28, 0,  0,   (0.12, 0.31, 0.47)),
    "h1":     ("F2", 15, True, 20, 16, 0,   (0.12, 0.31, 0.47)),
    "h2":     ("F2", 12, True, 16, 10, 0,   (0.20, 0.20, 0.20)),
    "body":   ("F1", 10.5, False, 14, 4, 0, (0.10, 0.10, 0.10)),
    "bullet": ("F1", 10.5, False, 14, 2, 16, (0.10, 0.10, 0.10)),
    "code":   ("F3", 9.5, False, 12.5, 4, 12, (0.15, 0.15, 0.15)),
    "small":  ("F1", 8.5, False, 11, 6, 0,  (0.40, 0.40, 0.40)),
    "spacer": ("F1", 10, False, 8, 0, 0,    (0, 0, 0)),
}

FONT_NAMES = {"F1": "Helvetica", "F2": "Helvetica-Bold", "F3": "Courier"}


def _layout(blocks: List[Block]) -> List[List[Tuple]]:
    """Turn blocks into pages of drawing ops.

    Each op: (font, size, r, g, b, x, y, text).
    """
    pages: List[List[Tuple]] = []
    ops: List[Tuple] = []
    y = PAGE_H - MARGIN_T

    def new_page():
        nonlocal ops, y
        pages.append(ops)
        ops = []
        y = PAGE_H - MARGIN_T

    for blk in blocks:
        font, size, bold, leading, space_before, indent, color = STYLES[blk.style]
        y -= space_before
        if blk.style == "spacer":
            continue
        prefix = ""
        if blk.style == "bullet":
            prefix = "\u2022  "  # bullet + spaces
        max_w = CONTENT_W - indent - _text_width(prefix, size, bold)
        # code blocks: don't wrap on spaces aggressively; wrap by width anyway
        lines = _wrap(blk.text, size, bold, max_w)
        first = True
        for ln in lines:
            if y - leading < MARGIN_B:
                new_page()
            x = MARGIN_L + indent
            draw = (prefix + ln) if (first and prefix) else \
                   (("   " + ln) if prefix else ln)
            ops.append((font, size, color[0], color[1], color[2], x, y,
                        _esc(draw)))
            y -= leading
            first = False

    if ops:
        pages.append(ops)
    return pages


def build_pdf(blocks: List[Block], path: str, footer: str = "") -> str:
    pages = _layout(blocks)
    # --- assemble PDF objects ---
    objects: List[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)  # 1-based object number

    # Fonts (WinAnsiEncoding so bytes 0x91-0x97 render as curly quotes/dashes/bullet)
    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
             b"/Encoding /WinAnsiEncoding >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
             b"/Encoding /WinAnsiEncoding >>")
    f3 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier "
             b"/Encoding /WinAnsiEncoding >>")
    font_res = ("<< /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >>"
                % (f1, f2, f3)).encode("latin-1")

    page_obj_nums: List[int] = []
    content_obj_nums: List[int] = []
    # Reserve: we need the Pages object number before pages reference it.
    # We'll create content + page objects, collecting numbers, then Pages, then
    # patch /Parent. Simpler: compute Pages number in advance.
    # Layout of objects from here:
    #   for each page: content stream obj, then page obj
    #   then Pages, then Catalog.
    n_pages = len(pages)
    first_dynamic = len(objects) + 1
    pages_obj_num = first_dynamic + n_pages * 2  # after all content+page objs

    total_pages = n_pages
    for pi, ops in enumerate(pages, start=1):
        parts = ["BT"]
        cur_font = None
        cur_size = None
        cur_color = None
        for (font, size, r, g, b, x, y, text) in ops:
            if (r, g, b) != cur_color:
                parts.append("%.3f %.3f %.3f rg" % (r, g, b))
                cur_color = (r, g, b)
            if font != cur_font or size != cur_size:
                parts.append("/%s %.2f Tf" % (font, size))
                cur_font, cur_size = font, size
            parts.append("1 0 0 1 %.2f %.2f Tm (%s) Tj" % (x, y, text))
        # footer
        if footer:
            foot = _esc("%s   —   página %d de %d" % (footer, pi, total_pages))
            parts.append("0.5 0.5 0.5 rg")
            parts.append("/F1 8.00 Tf")
            parts.append("1 0 0 1 %.2f %.2f Tm (%s) Tj" % (MARGIN_L, 40.0, foot))
        parts.append("ET")
        stream = ("\n".join(parts)).encode("latin-1")
        stream_c = zlib.compress(stream)
        content = (b"<< /Length %d /Filter /FlateDecode >>\nstream\n" %
                   len(stream_c)) + stream_c + b"\nendstream"
        cnum = add(content)
        content_obj_nums.append(cnum)
        page = ("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.0f %.0f] "
                "/Resources %s /Contents %d 0 R >>"
                % (pages_obj_num, PAGE_W, PAGE_H, font_res.decode("latin-1"), cnum)
                ).encode("latin-1")
        pnum = add(page)
        page_obj_nums.append(pnum)

    kids = " ".join("%d 0 R" % n for n in page_obj_nums)
    pages_obj = ("<< /Type /Pages /Count %d /Kids [%s] >>"
                 % (n_pages, kids)).encode("latin-1")
    real_pages_num = add(pages_obj)
    assert real_pages_num == pages_obj_num, (real_pages_num, pages_obj_num)
    catalog_num = add(("<< /Type /Catalog /Pages %d 0 R >>"
                       % pages_obj_num).encode("latin-1"))

    # --- write file with xref ---
    out = bytearray()
    out += b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0] * (len(objects) + 1)
    for i, obj in enumerate(objects, start=1):
        offsets[i] = len(out)
        out += ("%d 0 obj\n" % i).encode("latin-1") + obj + b"\nendobj\n"
    xref_pos = len(out)
    n_objs = len(objects) + 1
    out += ("xref\n0 %d\n" % n_objs).encode("latin-1")
    out += b"0000000000 65535 f \n"
    for i in range(1, n_objs):
        out += ("%010d 00000 n \n" % offsets[i]).encode("latin-1")
    out += ("trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (n_objs, catalog_num, xref_pos)).encode("latin-1")

    with open(path, "wb") as fh:
        fh.write(out)
    return path
