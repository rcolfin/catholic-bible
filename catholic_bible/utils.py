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
from catholic_bible.models import Language, VerseRef

logger = logging.getLogger(__name__)

_FOOTNOTE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{8}-[a-z]$", re.IGNORECASE)
_CROSS_REF_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z*]\.\s*(?:\[.*?\]\s*)?",
    re.IGNORECASE,
)
_VERSE_RANGE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+)[\u2013\-](\d+)")


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


def lookup_book(
    key: str | None,
    language: Language = Language.ENGLISH,
) -> BibleBookInfo | None:
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
    ot_lookup = _get_old_testament_book_lookup(language)
    nt_lookup = _get_new_testament_book_lookup(language)
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


@lru_cache(maxsize=2)
def _get_old_testament_book_lookup(language: Language = Language.ENGLISH) -> dict[str, BibleBookInfo]:
    """Returns a lookup dict for Old Testament books."""
    return _build_book_lookup(constants.OLD_TESTAMENT_BOOKS, language)


@lru_cache(maxsize=2)
def _get_new_testament_book_lookup(language: Language = Language.ENGLISH) -> dict[str, BibleBookInfo]:
    """Returns a lookup dict for New Testament books."""
    return _build_book_lookup(constants.NEW_TESTAMENT_BOOKS, language)


def _build_book_lookup(
    books: Iterable[BibleBookInfo], language: Language = Language.ENGLISH
) -> dict[str, BibleBookInfo]:
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

        if language == Language.SPANISH:
            if book.spanish_short_abbreviation:
                abbrev_lookup[book.spanish_short_abbreviation.casefold()].append(book)
            if book.spanish_long_abbreviation and book.spanish_long_abbreviation != book.spanish_short_abbreviation:
                abbrev_lookup[book.spanish_long_abbreviation.casefold()].append(book)
        else:
            abbrev_lookup[short_abbrev].append(book)

    for abbrev, book_list in abbrev_lookup.items():
        if len(book_list) > 1:
            logger.info("Skipping ambiguous abbreviation: %s", abbrev)
            continue
        lookup[abbrev] = book_list[0]

    return lookup


def _consume_book_prefix(
    group: str,
    language: Language,
    current_book: BibleBookInfo | str | None,
) -> tuple[BibleBookInfo | str | None, str]:
    """Returns (book, remaining_group) after consuming a leading book abbreviation, if present.

    Handles plain abbreviations (``Gn 1:1``) and numbered-book abbreviations
    (``2 Cor 4:6`` where the digit prefix is a separate token).
    Returns the unchanged current_book and group unchanged if no book prefix is detected.
    """
    parts = group.split(None, 1)
    if not parts or ":" in parts[0]:
        return current_book, group

    token = parts[0]
    remainder = parts[1] if len(parts) > 1 else ""

    if token.isdigit() and remainder:
        next_parts = remainder.split(None, 1)
        combined = lookup_book(f"{token} {next_parts[0]}", language)
        if combined is not None:
            return combined, next_parts[1] if len(next_parts) > 1 else ""
        return token, remainder

    resolved = lookup_book(token, language)
    return (resolved if resolved is not None else token), remainder


def _parse_verse_range(verse_part: str) -> tuple[int, int]:
    """Parses a verse part string into a (start_verse, end_verse) tuple.

    Handles single verses (e.g. ``'3'``) and en-dash/hyphen ranges (e.g. ``'5\u20136'`` or ``'1-3'``).

    Raises:
        ValueError: if the verse part cannot be parsed.
    """
    stripped = verse_part.strip()
    range_match = _VERSE_RANGE_PATTERN.match(stripped)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    verse = int(stripped)
    return verse, verse


def parse_cross_references(
    text: str,
    language: Language = Language.ENGLISH,
) -> list[VerseRef]:
    """Parses a USCCB cross-reference string into a list of VerseRef objects.

    Strips the leading footnote letter and optional source context, then walks
    semicolon-separated groups maintaining current book and chapter state.

    Args:
        text: A raw USCCB cross-reference string,
            e.g. ``"l. [1:26\\u201327] Gn 5:1, 3; 9:6; Ps 8:5\\u20136."``.
        language: The language of the abbreviations in ``text`` (default ENGLISH).

    Returns:
        Ordered list of VerseRef objects.

    >>> refs = parse_cross_references("a. Gn 1:1.")
    >>> refs[0].to_dict()
    {'book': 'genesis', 'chapter': 1, 'start_verse': 1, 'end_verse': 1}
    >>> refs = parse_cross_references("b. Gn 5:1, 3.")
    >>> refs[0].to_dict()
    {'book': 'genesis', 'chapter': 5, 'start_verse': 1, 'end_verse': 1}
    >>> refs[1].to_dict()
    {'book': 'genesis', 'chapter': 5, 'start_verse': 3, 'end_verse': 3}
    """
    body = _CROSS_REF_PREFIX_PATTERN.sub("", text).rstrip(".")
    result: list[VerseRef] = []
    current_book: BibleBookInfo | str | None = None
    current_chapter: int | None = None

    for raw_group in body.split(";"):
        group = raw_group.strip()
        if not group:
            continue

        # Detect a book abbreviation: first token has no ':'
        current_book, group = _consume_book_prefix(group, language, current_book)

        if current_book is None:
            logger.warning("Cross-reference group has no book context, skipping: %r", group)
            continue

        for raw_item in group.split(","):
            item = raw_item.strip()
            if not item:
                continue
            try:
                if ":" in item:
                    ch_str, verse_part = item.split(":", 1)
                    current_chapter = int(ch_str.strip())
                    start_verse, end_verse = _parse_verse_range(verse_part)
                    result.append(VerseRef(current_book, current_chapter, start_verse, end_verse))
                elif current_chapter is None:
                    # bare number/range with no chapter context → chapter-only reference
                    range_match = _VERSE_RANGE_PATTERN.match(item)
                    if range_match:
                        result.append(
                            VerseRef(current_book, int(range_match.group(1)), None, None, int(range_match.group(2)))
                        )
                    else:
                        result.append(VerseRef(current_book, int(item.strip()), None, None))
                else:
                    start_verse, end_verse = _parse_verse_range(item)
                    result.append(VerseRef(current_book, current_chapter, start_verse, end_verse))
            except ValueError:
                logger.warning("Could not parse cross-reference item: %r", item)

    return result
