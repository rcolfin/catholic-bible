from __future__ import annotations

import pytest

from catholic_bible.models import BibleChapter, BibleSection, BibleVerse, Language

# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------


def test_language_english_url_prefix() -> None:
    assert Language.ENGLISH.url_prefix == ""


def test_language_spanish_url_prefix() -> None:
    assert Language.SPANISH.url_prefix == "es/"


def test_language_case_insensitive() -> None:
    assert Language("english") == Language.ENGLISH
    assert Language("ENGLISH") == Language.ENGLISH
    assert Language("Spanish") == Language.SPANISH


# ---------------------------------------------------------------------------
# BibleVerse
# ---------------------------------------------------------------------------


def test_bible_verse_to_dict_no_footnotes() -> None:
    v = BibleVerse(1, "In the beginning.", [])
    d = v.to_dict()
    assert d == {"number": 1, "text": "In the beginning."}
    assert "footnote_refs" not in d


def test_bible_verse_to_dict_with_footnotes() -> None:
    v = BibleVerse(1, "In the beginning.", ["a", "b"])
    d = v.to_dict()
    assert d["footnote_refs"] == ["a", "b"]


def test_bible_verse_str() -> None:
    v = BibleVerse(3, "Then God said: Let there be light.", [])
    assert str(v) == "3 Then God said: Let there be light."


def test_bible_verse_str_with_footnote() -> None:
    v = BibleVerse(1, "In the beginning.", ["a"])
    assert str(v) == "1[a] In the beginning."


# ---------------------------------------------------------------------------
# BibleSection
# ---------------------------------------------------------------------------


def test_bible_section_to_dict_with_heading() -> None:
    v = BibleVerse(1, "Verse text.", [])
    s = BibleSection("My Heading.", [v])
    d = s.to_dict()
    assert d["heading"] == "My Heading."
    assert len(d["verses"]) == 1


def test_bible_section_to_dict_no_heading() -> None:
    v = BibleVerse(1, "Verse text.", [])
    s = BibleSection(None, [v])
    d = s.to_dict()
    assert "heading" not in d


# ---------------------------------------------------------------------------
# BibleChapter
# ---------------------------------------------------------------------------


def test_bible_chapter_verses_flat() -> None:
    v1 = BibleVerse(1, "First verse.", [])
    v2 = BibleVerse(2, "Second verse.", [])
    s = BibleSection("Heading", [v1, v2])
    chapter = BibleChapter("genesis", 1, Language.ENGLISH, "http://example.com", "Genesis 1", [s])
    assert chapter.verses == [v1, v2]


def test_bible_chapter_get_verse_found() -> None:
    v1 = BibleVerse(1, "First verse.", [])
    v2 = BibleVerse(2, "Second verse.", [])
    s = BibleSection(None, [v1, v2])
    chapter = BibleChapter("genesis", 1, Language.ENGLISH, "http://example.com", "Genesis 1", [s])
    assert chapter.get_verse(2) == v2


def test_bible_chapter_get_verse_not_found() -> None:
    s = BibleSection(None, [BibleVerse(1, "First verse.", [])])
    chapter = BibleChapter("genesis", 1, Language.ENGLISH, "http://example.com", "Genesis 1", [s])
    assert chapter.get_verse(99) is None


def test_bible_chapter_to_dict() -> None:
    v = BibleVerse(1, "First verse.", [])
    s = BibleSection("Heading", [v])
    chapter = BibleChapter("genesis", 1, Language.ENGLISH, "https://example.com", "Genesis, Chapter 1", [s])
    d = chapter.to_dict()
    assert d["book"] == "genesis"
    assert d["number"] == 1
    assert d["language"] == "english"
    assert d["title"] == "Genesis, Chapter 1"
    assert len(d["sections"]) == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ENGLISH", Language.ENGLISH),
        ("english", Language.ENGLISH),
        ("Spanish", Language.SPANISH),
        ("SPANISH", Language.SPANISH),
    ],
)
def test_language_case_insensitive_parametrized(value: str, expected: Language) -> None:
    assert Language(value) == expected


def test_language_repr() -> None:
    assert repr(Language.ENGLISH) == "ENGLISH"
    assert repr(Language.SPANISH) == "SPANISH"


# ---------------------------------------------------------------------------
# BibleVerse repr
# ---------------------------------------------------------------------------


def test_bible_verse_repr_short() -> None:
    v = BibleVerse(1, "In the beginning.", [])
    assert repr(v) == "1: In the beginning."


def test_bible_verse_repr_truncated() -> None:
    long_text = "a" * 70
    v = BibleVerse(2, long_text, [])
    r = repr(v)
    assert r.endswith("...")
    assert "a" * 60 in r


# ---------------------------------------------------------------------------
# BibleSection repr / str
# ---------------------------------------------------------------------------


def test_bible_section_repr_with_heading() -> None:
    s = BibleSection("The Heading.", [BibleVerse(1, "text", [])])
    assert repr(s) == "The Heading. [1 verses]"


def test_bible_section_repr_no_heading() -> None:
    s = BibleSection(None, [])
    assert repr(s) == "(no heading) [0 verses]"


def test_bible_section_str_with_heading() -> None:
    v = BibleVerse(1, "First verse.", [])
    s = BibleSection("Heading", [v])
    assert str(s) == "Heading\n1 First verse."


def test_bible_section_str_no_heading() -> None:
    v = BibleVerse(1, "First verse.", [])
    s = BibleSection(None, [v])
    assert str(s) == "1 First verse."


# ---------------------------------------------------------------------------
# BibleChapter repr / str
# ---------------------------------------------------------------------------


def test_bible_chapter_repr() -> None:
    chapter = BibleChapter("genesis", 1, Language.ENGLISH, "http://example.com", "Genesis, Chapter 1", [])
    assert repr(chapter) == "Genesis, Chapter 1 (ENGLISH)"


def test_bible_chapter_str_contains_title_and_url() -> None:
    v = BibleVerse(1, "First verse.", [])
    s = BibleSection(None, [v])
    chapter = BibleChapter("genesis", 1, Language.ENGLISH, "http://example.com", "Genesis, Chapter 1", [s])
    result = str(chapter)
    assert "Genesis, Chapter 1" in result
    assert "http://example.com" in result
    assert "1 First verse." in result
