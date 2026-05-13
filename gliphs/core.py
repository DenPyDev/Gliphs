from __future__ import annotations

import hashlib
import io
import random
from pathlib import Path
from typing import Iterable

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from .charset import (
    build_charset,
    contains_rtl,
    iter_bidi_safe_chunks,
)

PUA_START = 0xE000
PUA_END = 0xF8FF
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FONT = PROJECT_ROOT / "fonts" / "DejaVuSans.ttf"
DEFAULT_DOCS_DIR = PROJECT_ROOT / "docs"


def build_pua_maps(chars: Iterable[str], seed: int | None = None) -> tuple[dict[str, str], dict[str, str]]:
    source_chars = list(dict.fromkeys(chars))
    if len(source_chars) > PUA_END - PUA_START + 1:
        raise ValueError("Too many encoded characters for BMP Private Use Area")

    slots = [chr(PUA_START + index) for index in range(len(source_chars))]
    random.Random(seed).shuffle(slots)
    source_to_slot = dict(zip(source_chars, slots))
    slot_to_source = {slot: source for source, slot in source_to_slot.items()}
    return slot_to_source, source_to_slot


def encode_text(text: str, source_to_slot: dict[str, str]) -> str:
    chunks: list[str] = []
    for chunk, may_encode in iter_bidi_safe_chunks(text):
        chunks.append("".join(source_to_slot.get(ch, ch) for ch in chunk) if may_encode else chunk)
    return "".join(chunks)


def phrase_to_seed(phrase: str) -> int:
    return int.from_bytes(hashlib.sha256(phrase.encode()).digest()[:4], "big")


def get_best_cmap(font: TTFont) -> dict[int, str]:
    cmap = font.getBestCmap()
    if not cmap:
        raise ValueError("Font has no usable cmap table")
    return dict(cmap)


def _build_cmap_tables(mapping: dict[int, str]) -> list[CmapSubtable]:
    def subtable(fmt: int, platform: int, encoding: int, cmap: dict[int, str]) -> CmapSubtable:
        table = CmapSubtable.newSubtable(fmt)
        table.platformID = platform
        table.platEncID = encoding
        table.language = 0
        table.cmap = dict(cmap)
        return table

    bmp = {codepoint: name for codepoint, name in mapping.items() if codepoint <= 0xFFFF}
    non_bmp = {codepoint: name for codepoint, name in mapping.items() if codepoint > 0xFFFF}

    tables = [subtable(4, 3, 1, bmp), subtable(4, 0, 3, bmp)]
    if non_bmp:
        full = {**bmp, **non_bmp}
        tables.extend([subtable(12, 3, 10, full), subtable(12, 0, 4, full)])
    return tables


def build_pua_font_bytes(source_font: str | Path, slot_to_source: dict[str, str]) -> bytes:
    with TTFont(str(source_font)) as font:
        original = get_best_cmap(font)
        merged = dict(original)
        for slot, source in slot_to_source.items():
            glyph_name = original.get(ord(source))
            if glyph_name:
                merged[ord(slot)] = glyph_name

        font["cmap"].tables = _build_cmap_tables(merged)
        buffer = io.BytesIO()
        font.save(buffer)
        return buffer.getvalue()


def build_obfuscated_font_for_text(
    font_path: str | Path,
    text: str,
    output_font: str | Path,
    seed: int | None = None,
):
    chars = build_charset(text, font_path)
    slot_to_source, source_to_slot = build_pua_maps(chars, seed=seed)
    Path(output_font).write_bytes(build_pua_font_bytes(font_path, slot_to_source))

    encoded_text = encode_text(text, source_to_slot)
    passthrough = sorted(set(text) - set(source_to_slot))
    rtl_lines = [
        chunk
        for chunk, may_encode in iter_bidi_safe_chunks(text)
        if chunk.strip() and not may_encode and contains_rtl(chunk)
    ]
    diagnostics = {
        "font": str(font_path),
        "encoded_count": len(source_to_slot),
        "passthrough_count": len(passthrough),
        "encoded_chars": "".join(sorted(source_to_slot)),
        "passthrough_chars": "".join(passthrough),
        "rtl_lines_left_unencoded_count": len(rtl_lines),
        "rtl_lines_left_unencoded": rtl_lines,
        "map": {ch: f"U+{ord(slot):04X}" for ch, slot in sorted(source_to_slot.items())},
        "encoded_text": encoded_text,
    }
    return output_font, source_to_slot, diagnostics


def generate_docs_files(
    text: str,
    *,
    docs_dir: str | Path = DEFAULT_DOCS_DIR,
    source_font: str | Path = DEFAULT_FONT,
    name: str = "gliphs-demo",
    seed: str | int | None = "demo",
) -> tuple[Path, Path]:
    docs_dir = Path(docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    font_path = docs_dir / f"{name}.ttf"
    text_path = docs_dir / f"{name}.txt"
    numeric_seed = phrase_to_seed(seed) if isinstance(seed, str) else seed

    _, source_to_slot, _ = build_obfuscated_font_for_text(
        source_font,
        text,
        font_path,
        seed=numeric_seed,
    )
    text_path.write_text(encode_text(text, source_to_slot), encoding="utf-8")

    return font_path, text_path
