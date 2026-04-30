from __future__ import annotations

import pytest

from catholic_bible.constants import BibleBookInfo
from catholic_bible.errors import InvalidBookError
from catholic_bible.models import Language, VerseRef
from catholic_bible.utils import book_url_name, is_footnote_id, lookup_book, parse_cross_references


def test_lookup_book_by_full_name() -> None:
    result = lookup_book("Genesis")
    assert result.name == "Genesis"


def test_lookup_book_by_url_name() -> None:
    assert lookup_book("genesis").name == "Genesis"
    assert lookup_book("1corinthians").name == "1 Corinthians"
    assert lookup_book("songofsongs").name == "Song of Songs"


def test_lookup_book_by_long_abbreviation() -> None:
    assert lookup_book("Gen").name == "Genesis"
    assert lookup_book("1Cor").name == "1 Corinthians"


def test_lookup_book_by_short_abbreviation() -> None:
    assert lookup_book("Gn").name == "Genesis"


def test_lookup_book_case_insensitive() -> None:
    assert lookup_book("GENESIS").name == "Genesis"
    assert lookup_book("genesis").name == "Genesis"


def test_lookup_book_none() -> None:
    with pytest.raises(InvalidBookError):
        lookup_book(None)


def test_lookup_book_unknown() -> None:
    with pytest.raises(InvalidBookError):
        lookup_book("notabook")


def test_book_url_name_simple() -> None:
    book = BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50)
    assert book_url_name(book) == "genesis"


def test_book_url_name_numbered() -> None:
    book = BibleBookInfo("1 Samuel", "First Book of Samuel", "1Sm", "1Sam", 31)
    assert book_url_name(book) == "1samuel"


def test_book_url_name_multi_word() -> None:
    book = BibleBookInfo("Song of Songs", "Song of Songs", "Sg", "Song", 8)
    assert book_url_name(book) == "songofsongs"


def test_book_url_name_corinthians() -> None:
    book = BibleBookInfo("1 Corinthians", "First Letter of Saint Paul to the Corinthians", "1C", "1Cor", 16)
    assert book_url_name(book) == "1corinthians"


@pytest.mark.parametrize(
    ("anchor_id", "expected"),
    [
        ("01001001-a", True),
        ("99150001-z", True),
        ("fn-01001001-a", False),
        ("chapter-1", False),
        ("", False),
    ],
)
def test_is_footnote_id(anchor_id: str, expected: bool) -> None:  # noqa: FBT001
    assert is_footnote_id(anchor_id) == expected


def test_lookup_book_new_testament() -> None:
    result = lookup_book("matthew")
    assert result.name == "Matthew"


def test_lookup_book_new_testament_numbered() -> None:
    result = lookup_book("1john")
    assert result.name == "1 John"


def test_lookup_book_with_spaces() -> None:
    result = lookup_book("Song of Songs")
    assert result.name == "Song of Songs"


def test_lookup_book_long_abbreviation_nt() -> None:
    assert lookup_book("Matt").name == "Matthew"
    assert lookup_book("Rev").name == "Revelation"


def test_book_url_name_new_testament() -> None:
    book = BibleBookInfo("1 John", "First Letter of Saint John", "1Jn", "1John", 5)
    assert book_url_name(book) == "1john"


def test_lookup_book_spanish_psalms() -> None:
    result = lookup_book("Sal", Language.SPANISH)
    assert result.name == "Psalms"


def test_lookup_book_spanish_revelation() -> None:
    result = lookup_book("Ap", Language.SPANISH)
    assert result.name == "Revelation"


# ---------------------------------------------------------------------------
# parse_cross_references
# ---------------------------------------------------------------------------


def test_parse_cross_references_full_example() -> None:
    text = (
        "l. [1:26\u201327] Gn 5:1, 3; 9:6; Ps 8:5\u20136; Wis 2:23; 10:2;"
        " Sir 17:1, 3\u20134; Mt 19:4; Mk 10:6; Jas 3:7; Eph 4:24; Col 3:10."
    )
    refs = parse_cross_references(text)
    assert len(refs) == 13  # noqa: PLR2004
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 1, "end_verse": 1}
    assert refs[1].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 3, "end_verse": 3}
    assert refs[2].to_dict() == {"book": "genesis", "chapter": 9, "start_verse": 6, "end_verse": 6}
    assert refs[3].to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}
    assert refs[4].to_dict() == {"book": "wisdom", "chapter": 2, "start_verse": 23, "end_verse": 23}
    assert refs[5].to_dict() == {"book": "wisdom", "chapter": 10, "start_verse": 2, "end_verse": 2}
    assert refs[6].to_dict() == {"book": "sirach", "chapter": 17, "start_verse": 1, "end_verse": 1}
    assert refs[7].to_dict() == {"book": "sirach", "chapter": 17, "start_verse": 3, "end_verse": 4}
    assert refs[8].to_dict() == {"book": "matthew", "chapter": 19, "start_verse": 4, "end_verse": 4}
    assert refs[9].to_dict() == {"book": "mark", "chapter": 10, "start_verse": 6, "end_verse": 6}
    assert refs[10].to_dict() == {"book": "james", "chapter": 3, "start_verse": 7, "end_verse": 7}
    assert refs[11].to_dict() == {"book": "ephesians", "chapter": 4, "start_verse": 24, "end_verse": 24}
    assert refs[12].to_dict() == {"book": "colossians", "chapter": 3, "start_verse": 10, "end_verse": 10}


def test_parse_cross_references_single_verse() -> None:
    refs = parse_cross_references("a. Gn 1:1.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 1, "start_verse": 1, "end_verse": 1}


def test_parse_cross_references_verse_range() -> None:
    refs = parse_cross_references("b. Ps 8:5\u20136.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}


def test_parse_cross_references_book_carry() -> None:
    refs = parse_cross_references("c. Gn 1:1; 2:3.")
    assert len(refs) == 2  # noqa: PLR2004
    assert refs[0].to_dict()["book"] == "genesis"
    assert refs[1].to_dict()["book"] == "genesis"
    assert refs[1].to_dict()["chapter"] == 2  # noqa: PLR2004


def test_parse_cross_references_chapter_carry() -> None:
    refs = parse_cross_references("d. Gn 5:1, 3.")
    assert len(refs) == 2  # noqa: PLR2004
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 1, "end_verse": 1}
    assert refs[1].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 3, "end_verse": 3}


def test_parse_cross_references_unresolved_book() -> None:
    refs = parse_cross_references("e. Xyz 1:1.")
    assert len(refs) == 1
    assert refs[0].book == "Xyz"
    assert refs[0].to_dict()["book"] == "Xyz"


def test_parse_cross_references_hyphen_range() -> None:
    refs = parse_cross_references("f. Gn 1:1-3.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 1, "start_verse": 1, "end_verse": 3}


def test_parse_cross_references_spanish() -> None:
    refs = parse_cross_references("a. Sal 8:5\u20136.", Language.SPANISH)
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}


def test_parse_cross_references_returns_verse_ref_type() -> None:
    refs = parse_cross_references("a. Gn 1:1.")
    assert isinstance(refs[0], VerseRef)


def test_parse_cross_references_numbered_book_single() -> None:
    refs = parse_cross_references("c. [1:3] 2 Cor 4:6.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "2corinthians", "chapter": 4, "start_verse": 6, "end_verse": 6}


def test_parse_cross_references_numbered_book_mixed() -> None:
    refs = parse_cross_references("a. 1 Mc 7:28; 2 Mc 7:28.")
    assert len(refs) == 2  # noqa: PLR2004
    assert refs[0].to_dict() == {"book": "1maccabees", "chapter": 7, "start_verse": 28, "end_verse": 28}
    assert refs[1].to_dict() == {"book": "2maccabees", "chapter": 7, "start_verse": 28, "end_verse": 28}


def test_parse_cross_references_chapter_only() -> None:
    refs = parse_cross_references("i. [2:55] Jos 1, 2, 5.")
    assert len(refs) == 3  # noqa: PLR2004
    assert refs[0].to_dict() == {"book": "joshua", "chapter": 1}
    assert refs[1].to_dict() == {"book": "joshua", "chapter": 2}
    assert refs[2].to_dict() == {"book": "joshua", "chapter": 5}


def test_parse_cross_references_chapter_only_no_verses() -> None:
    refs = parse_cross_references("i. [2:55] Jos 1, 2, 5.")
    for ref in refs:
        assert ref.start_verse is None
        assert ref.end_verse is None


def test_parse_cross_references_chapter_range() -> None:
    # "Sir 37-45" - a range of chapters with no verse context (e.g. Wisdom 10 footnotes)
    refs = parse_cross_references("a. Sir 37\u201345.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "sirach", "chapter": 37, "end_chapter": 45}


# ---------------------------------------------------------------------------
# lookup_book fuzzy matching tests
# ---------------------------------------------------------------------------


class TestLookupBookFuzzyMatching:
    def test_lookup_book_with_close_match(self) -> None:
        """lookup_book should suggest closest match for typo."""
        with pytest.raises(InvalidBookError) as exc_info:
            lookup_book("corinthians")

        error = exc_info.value
        assert error.book_name == "corinthians"
        assert error.closest_match in ["1 Corinthians", "2 Corinthians"]
        # One of the two should be the closest

    def test_lookup_book_with_no_close_match(self) -> None:
        """lookup_book should not suggest match for very different names."""
        with pytest.raises(InvalidBookError) as exc_info:
            lookup_book("xyz")

        error = exc_info.value
        assert error.book_name == "xyz"
        assert error.closest_match is None

    def test_lookup_book_valid_name_still_works(self) -> None:
        """lookup_book should still work correctly for valid book names."""
        # Test a few common variations
        genesis = lookup_book("Genesis")
        assert genesis.name == "Genesis"

        matthew = lookup_book("matthew")
        assert matthew.name == "Matthew"

        psalms = lookup_book("psalms")
        assert psalms.name == "Psalms"

    def test_lookup_book_with_partial_match(self) -> None:
        """lookup_book should handle partial matches."""
        with pytest.raises(InvalidBookError) as exc_info:
            lookup_book("genisis")  # typo of genesis

        error = exc_info.value
        assert error.closest_match == "Genesis"

    def test_lookup_book_case_insensitive(self) -> None:
        """lookup_book should still be case insensitive for valid names."""
        genesis1 = lookup_book("GENESIS")
        genesis2 = lookup_book("genesis")
        assert genesis1.name == genesis2.name == "Genesis"
