from fontTools.ttLib import TTFont

from gliphs.core import DEFAULT_FONT, build_obfuscated_font_for_text, encode_text, generate_docs_files


def test_generated_font_renders_encoded_slots(tmp_path):
    text = "ABЯΩ"
    font_path = tmp_path / "gliphs.ttf"

    _, source_to_slot, info = build_obfuscated_font_for_text(DEFAULT_FONT, text, font_path, seed=2)
    encoded = encode_text(text, source_to_slot)

    assert font_path.exists()
    assert encoded != text
    assert info["encoded_count"] == len(source_to_slot)

    with TTFont(str(DEFAULT_FONT)) as source_font, TTFont(str(font_path)) as generated_font:
        source_cmap = source_font.getBestCmap()
        generated_cmap = generated_font.getBestCmap()
        for source, slot in source_to_slot.items():
            assert generated_cmap[ord(slot)] == source_cmap[ord(source)]


def test_generate_docs_files_writes_only_font_and_text(tmp_path):
    font_path, text_path = generate_docs_files("Hello ЯΩ", docs_dir=tmp_path, seed="test")

    assert font_path == tmp_path / "gliphs-demo.ttf"
    assert text_path == tmp_path / "gliphs-demo.txt"
    assert font_path.exists()
    assert text_path.exists()
    assert text_path.read_text(encoding="utf-8") != "Hello ЯΩ"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gliphs-demo.ttf", "gliphs-demo.txt"]
