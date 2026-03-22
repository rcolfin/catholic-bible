from __future__ import annotations

import pytest

from catholic_bible.constants import BibleBookInfo
from catholic_bible.utils import book_url_name, is_footnote_id, lookup_book


def test_lookup_book_by_full_name() -> None:
    result = lookup_book("Genesis")
    assert result is not None
    assert result.name == "Genesis"


def test_lookup_book_by_url_name() -> None:
    assert lookup_book("genesis").name == "Genesis"  # type: ignore[union-attr]
    assert lookup_book("1corinthians").name == "1 Corinthians"  # type: ignore[union-attr]
    assert lookup_book("songofsongs").name == "Song of Songs"  # type: ignore[union-attr]


def test_lookup_book_by_long_abbreviation() -> None:
    assert lookup_book("Gen").name == "Genesis"  # type: ignore[union-attr]
    assert lookup_book("1Cor").name == "1 Corinthians"  # type: ignore[union-attr]


def test_lookup_book_by_short_abbreviation() -> None:
    assert lookup_book("Gn").name == "Genesis"  # type: ignore[union-attr]


def test_lookup_book_case_insensitive() -> None:
    assert lookup_book("GENESIS").name == "Genesis"  # type: ignore[union-attr]
    assert lookup_book("genesis").name == "Genesis"  # type: ignore[union-attr]


def test_lookup_book_none() -> None:
    assert lookup_book(None) is None


def test_lookup_book_unknown() -> None:
    assert lookup_book("notabook") is None


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
    assert result is not None
    assert result.name == "Matthew"


def test_lookup_book_new_testament_numbered() -> None:
    result = lookup_book("1john")
    assert result is not None
    assert result.name == "1 John"


def test_lookup_book_with_spaces() -> None:
    result = lookup_book("Song of Songs")
    assert result is not None
    assert result.name == "Song of Songs"


def test_lookup_book_long_abbreviation_nt() -> None:
    assert lookup_book("Matt").name == "Matthew"  # type: ignore[union-attr]
    assert lookup_book("Rev").name == "Revelation"  # type: ignore[union-attr]


def test_book_url_name_new_testament() -> None:
    book = BibleBookInfo("1 John", "First Letter of Saint John", "1Jn", "1John", 5)
    assert book_url_name(book) == "1john"
