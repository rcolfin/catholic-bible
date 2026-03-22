from __future__ import annotations

import logging
import re
from collections import defaultdict
from functools import lru_cache
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable

from catholic_bible import constants
from catholic_bible.constants import BibleBookInfo  # noqa: TC001

logger = logging.getLogger(__name__)

_FOOTNOTE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{8}-[a-z]$", re.IGNORECASE)


def book_url_name(book: BibleBookInfo) -> str:
    """
    Returns the URL-safe name for a book, derived from its display name.

    Converts to lowercase and removes all spaces.

    >>> book_url_name(BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50))
    'genesis'
    >>> book_url_name(BibleBookInfo("1 Samuel", "First Book of Samuel", "1Sm", "1Sam", 31))
    '1samuel'
    >>> book_url_name(BibleBookInfo("Song of Songs", "Song of Songs", "Sg", "Song", 8))
    'songofsongs'
    >>> book_url_name(BibleBookInfo("1 Corinthians", "First Letter of Saint Paul to the Corinthians", "1C", "1Cor", 16))
    '1corinthians'
    """
    return book.name.lower().replace(" ", "")


def lookup_book(key: str | None) -> BibleBookInfo | None:
    """
    Looks up a book by name, URL name, or abbreviation (case-insensitive).

    >>> lookup_book("genesis").name
    'Genesis'
    >>> lookup_book("Genesis").name
    'Genesis'
    >>> lookup_book("1corinthians").name
    '1 Corinthians'
    >>> lookup_book("Gen").name
    'Genesis'
    >>> lookup_book("Gn").name
    'Genesis'
    >>> lookup_book(None) is None
    True
    >>> lookup_book("notabook") is None
    True
    """
    if key is None:
        return None

    key = key.replace(" ", "").strip().casefold()
    ot_lookup = _get_old_testament_book_lookup()
    nt_lookup = _get_new_testament_book_lookup()
    ot_book = ot_lookup.get(key)
    nt_book = nt_lookup.get(key)

    if ot_book:
        if nt_book:
            logger.warning("Ambiguous book key '%s' matches both testaments.", key)
            return None
        return ot_book

    return nt_book


def is_footnote_id(anchor_id: str) -> bool:
    """
    Returns True if the given anchor ID looks like a USCCB Bible footnote ID.

    Footnote IDs follow the pattern BBCCVVV-x (e.g. '01001001-a').

    >>> is_footnote_id("01001001-a")
    True
    >>> is_footnote_id("fn-01001001-a")
    False
    >>> is_footnote_id("chapter-1")
    False
    """
    return bool(_FOOTNOTE_ID_PATTERN.match(anchor_id))


@lru_cache(maxsize=1)
def _get_old_testament_book_lookup() -> dict[str, BibleBookInfo]:
    """Returns a lookup dict for Old Testament books."""
    return _build_book_lookup(constants.OLD_TESTAMENT_BOOKS)


@lru_cache(maxsize=1)
def _get_new_testament_book_lookup() -> dict[str, BibleBookInfo]:
    """Returns a lookup dict for New Testament books."""
    return _build_book_lookup(constants.NEW_TESTAMENT_BOOKS)


def _build_book_lookup(books: Iterable[BibleBookInfo]) -> dict[str, BibleBookInfo]:
    lookup: dict[str, BibleBookInfo] = {}
    abbrev_lookup: dict[str, list[BibleBookInfo]] = defaultdict(list)

    for book in books:
        name = book.name.casefold()
        long_abbrev = book.long_abbreviation.casefold()
        short_abbrev = book.short_abbreviation.casefold()
        url_name = book_url_name(book).casefold()

        assert long_abbrev not in lookup, f"{long_abbrev} already exists."  # noqa: S101
        assert name not in lookup, f"{name} already exists."  # noqa: S101

        lookup[long_abbrev] = book
        lookup[name] = book
        lookup[url_name] = book

        if " " in name:
            lookup[name.replace(" ", "")] = book

        abbrev_lookup[short_abbrev].append(book)

    for short_abbrev, book_list in abbrev_lookup.items():
        if len(book_list) > 1:
            logger.info("Skipping ambiguous short abbreviation: %s", short_abbrev)
            continue
        lookup[short_abbrev] = book_list[0]

    return lookup
