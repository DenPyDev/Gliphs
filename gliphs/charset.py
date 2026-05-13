from __future__ import annotations

import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

RTL_BIDI = {"R", "AL", "AN"}


def is_rtl_char(ch: str) -> bool:
    return unicodedata.bidirectional(ch) in RTL_BIDI


def contains_rtl(text: str) -> bool:
    return any(is_rtl_char(ch) for ch in text)


def iter_bidi_safe_chunks(text: str):
    for part in text.splitlines(keepends=True):
        line = part.rstrip("\r\n")
        newline = part[len(line):]
        if line:
            yield line, not contains_rtl(line)
        if newline:
            yield newline, False


def is_allowed_source_char(ch: str) -> bool:
    category = unicodedata.category(ch)
    codepoint = ord(ch)

    if is_rtl_char(ch):
        return False
    if category[0] in {"C", "M", "Z", "S"}:
        return False

    if 0x0021 <= codepoint <= 0x007E:
        return True
    if 0x00A1 <= codepoint <= 0x024F:
        return category[0] in {"L", "N", "P"}
    if 0x1E00 <= codepoint <= 0x1EFF:
        return category[0] == "L"
    if 0x0370 <= codepoint <= 0x03FF:
        return category[0] in {"L", "P"}
    if 0x1F00 <= codepoint <= 0x1FFF:
        return category[0] == "L"
    if 0x0400 <= codepoint <= 0x052F:
        return category[0] in {"L", "P"}

    return False


def _font_chars(font_path: str | Path) -> set[str]:
    with TTFont(str(font_path)) as font:
        cmap = font.getBestCmap()
    if not cmap:
        raise ValueError("Font has no usable cmap table")
    return {chr(codepoint) for codepoint in cmap}


def build_charset(text: str, font_path: str | Path) -> list[str]:
    supported = _font_chars(font_path)
    seen: set[str] = set()
    for chunk, may_encode in iter_bidi_safe_chunks(text):
        if may_encode:
            seen.update(chunk)
    return sorted(ch for ch in seen if ch in supported and is_allowed_source_char(ch))
