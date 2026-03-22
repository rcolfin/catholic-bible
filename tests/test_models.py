from __future__ import annotations

import pytest

from catholic_bible.constants import BibleBookInfo
from catholic_bible.models import BibleChapter, BibleFootnote, BibleSection, BibleVerse, Language, VerseRef
from catholic_bible.utils import lookup_book

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


def test_bible_footnote_to_dict_with_cross_references() -> None:
    book = lookup_book("jeremiah")
    assert book is not None
    fn = BibleFootnote("Jer 4:23", [VerseRef(book, 4, 23, 23)])
    d = fn.to_dict()
    assert "ref" not in d
    assert d["text"] == "Jer 4:23"
    assert "cross_references" in d
    assert d["cross_references"] == [{"book": "jeremiah", "chapter": 4, "start_verse": 23, "end_verse": 23}]


def test_bible_footnote_to_dict_omits_empty_cross_references() -> None:
    fn = BibleFootnote("narrative text", [])
    d = fn.to_dict()
    assert "ref" not in d
    assert d["text"] == "narrative text"
    assert "cross_references" not in d


def test_bible_verse_to_dict_no_footnotes() -> None:
    v = BibleVerse(1, "In the beginning.", [])
    d = v.to_dict()
    assert d == {"number": 1, "text": "In the beginning."}
    assert "footnotes" not in d


def test_bible_verse_to_dict_with_footnotes() -> None:
    v = BibleVerse(1, "In the beginning.", [BibleFootnote("note one", []), BibleFootnote("note two", [])])
    d = v.to_dict()
    assert d["footnotes"] == [{"text": "note one"}, {"text": "note two"}]


def test_bible_verse_str() -> None:
    v = BibleVerse(3, "Then God said: Let there be light.", [])
    assert str(v) == "3 Then God said: Let there be light."


def test_bible_verse_str_with_footnote() -> None:
    v = BibleVerse(1, "In the beginning.", [BibleFootnote("note", [])])
    assert str(v) == "1 In the beginning."


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


# ---------------------------------------------------------------------------
# VerseRef
# ---------------------------------------------------------------------------


def test_verse_ref_to_dict_resolved() -> None:
    book = BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50, "Gn", "Gén")
    ref = VerseRef(book, 5, 1, 1)
    assert ref.to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 1, "end_verse": 1}


def test_verse_ref_to_dict_range() -> None:
    book = BibleBookInfo("Psalms", "Book of Psalms", "Ps", "Psalms", 150, "Sal", "Sal")
    ref = VerseRef(book, 8, 5, 6)
    assert ref.to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}


def test_verse_ref_to_dict_unresolved() -> None:
    ref = VerseRef("UnknownBook", 1, 1, 1)
    assert ref.to_dict() == {"book": "UnknownBook", "chapter": 1, "start_verse": 1, "end_verse": 1}


def test_verse_ref_to_dict_always_includes_end_verse() -> None:
    book = BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50, "Gn", "Gén")
    ref = VerseRef(book, 1, 3, 3)
    d = ref.to_dict()
    assert "end_verse" in d
    assert d["end_verse"] == 3  # noqa: PLR2004


def test_verse_ref_chapter_only_to_dict_omits_verses() -> None:
    book = BibleBookInfo("Joshua", "Book of Joshua", "Jos", "Josh", 24, "Jos", "Jos")
    ref = VerseRef(book, 1, None, None)
    d = ref.to_dict()
    assert d == {"book": "joshua", "chapter": 1}
    assert "start_verse" not in d
    assert "end_verse" not in d


def test_verse_ref_chapter_only_construction() -> None:
    ref = VerseRef("Jos", 5, None, None)
    assert ref.chapter == 5  # noqa: PLR2004
    assert ref.start_verse is None
    assert ref.end_verse is None
