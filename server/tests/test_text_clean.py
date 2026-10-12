"""文本清洗工具单测（TDD：先于实现编写）。"""

from app.utils.text_clean import clean_text, count_words


def test_empty_returns_empty():
    assert clean_text("") == ""


def test_whitespace_only_returns_empty():
    assert clean_text("   \n\t  \n　　") == ""


def test_collapses_multiple_blank_lines():
    raw = "第一行\n\n\n第二行\n   \n第三行"
    assert clean_text(raw) == "第一行\n第二行\n第三行"


def test_trims_and_collapses_inner_spaces():
    assert clean_text("  a   b\t c  ") == "a b c"


def test_normalizes_crlf_and_cr():
    assert clean_text("a\r\nb\rc") == "a\nb\nc"


def test_count_words_ignores_whitespace():
    assert count_words("a b\nc") == 3
    assert count_words("") == 0
    assert count_words("   ") == 0
