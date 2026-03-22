from __future__ import annotations

import asyncio
import html
import logging
import re
from typing import TYPE_CHECKING, Final, cast
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString
from curl_cffi import requests

from catholic_bible import constants, models, utils

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from types import TracebackType

    from bs4.element import Tag

logger = logging.getLogger(__name__)

_FOOTNOTE_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z]+\.\s+(?:\[[^\]]+\]\s+|\d+:\d+:\s+)?")
_QUERY_DIGIT_PATTERN: Final[re.Pattern[str]] = re.compile(r"\d+")


def _clean_text(text: str) -> str:
    """Normalises whitespace and unescapes HTML entities in verse text."""
    text = html.unescape(text.replace("\xa0", " "))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_footnote_text(text: str) -> str:
    """Strips the leading reference label and verse location from a raw footnote string.

    Removes the ``X. [C:V] `` prefix (reference letter, dot, optional bracket location)
    and any trailing period.

    >>> _clean_footnote_text("a. [1:1] Gn 2:1; Ps 8:4.")
    'Gn 2:1; Ps 8:4'
    >>> _clean_footnote_text("a. [1:1] 2 Cor 4:6.")
    '2 Cor 4:6'
    >>> _clean_footnote_text("c. [1:3] Jer 4:23.")
    'Jer 4:23'
    >>> _clean_footnote_text("a. narrative text.")
    'narrative text'
    >>> _clean_footnote_text("a. 2:1: Lc 2:1-7.")
    'Lc 2:1-7'
    """
    text = _FOOTNOTE_PREFIX_PATTERN.sub("", text)
    return text.rstrip(".")


def _parse_bible_href(href: str) -> tuple[str, int, int | None] | None:
    """Extracts (book_url_name, chapter, verse) from a USCCB Bible anchor href.

    Handles both relative (``/bible/genesis/1?1``) and absolute
    (``https://bible.usccb.org/bible/genesis/1?1#...``) URLs.
    Chapter-only hrefs with no query (``/bible/genesis/37?#...``) return ``verse=None``.
    Returns ``None`` if the href is not a valid USCCB Bible verse link.
    """
    parsed = urlparse(href)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 3 or parts[0] != "bible":  # noqa: PLR2004
        return None
    chapter = None
    verse = None
    try:
        chapter = int(parts[2])
        if parsed.query:
            verse_m = _QUERY_DIGIT_PATTERN.match(parsed.query)
            verse = int(verse_m.group(0)) if verse_m else None
    except ValueError:
        return None
    return parts[1], chapter, verse


def _collect_footnote_anchors(
    tag: Tag,
) -> list[tuple[constants.BibleBookInfo | str, int, int | None] | None]:
    """Walks a footnote paragraph's children and returns a flat token list.

    Each token is either a ``(book, chapter, verse)`` triple parsed from a
    ``/bible/`` href, or ``None`` representing a dash range-separator.
    ``verse`` is ``None`` for chapter-only hrefs (empty query).
    Anchors inside ``[...]`` brackets (source-verse context) are skipped.
    """
    in_bracket = 0
    tokens: list[tuple[constants.BibleBookInfo | str, int, int | None] | None] = []
    for child in tag.children:
        if isinstance(child, NavigableString):
            s = str(child)
            in_bracket += s.count("[") - s.count("]")
            if in_bracket <= 0 and s.strip() in ("\u2013", "-"):
                tokens.append(None)
        elif in_bracket <= 0:
            child_tag = cast("Tag", child)
            if child_tag.name == "a":
                parsed_href = _parse_bible_href(str(child_tag.get("href", "")))
                if parsed_href is not None:
                    book_url, chapter, verse = parsed_href
                    resolved = utils.lookup_book(book_url)
                    book: constants.BibleBookInfo | str = resolved if resolved is not None else book_url
                    tokens.append((book, chapter, verse))
    return tokens


def _parse_verse_refs_from_footnote_tag(tag: Tag) -> list[models.VerseRef]:
    """Parses VerseRef objects from ``/bible/`` anchor hrefs within a footnote paragraph.

    Skips anchors inside ``[...]`` brackets (source verse context).
    Detects ranges when two consecutive valid anchors are separated by a dash.
    Chapter-only hrefs (verse=None) produce chapter-only VerseRef objects.
    Returns an empty list if no matching hrefs are found (caller falls back to text parsing).
    """
    tokens = _collect_footnote_anchors(tag)
    result: list[models.VerseRef] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token is None:
            i += 1
            continue
        book, chapter, start = token
        if i + 2 < len(tokens) and tokens[i + 1] is None and tokens[i + 2] is not None:
            end = tokens[i + 2]
            if start is None and end[2] is None:  # type: ignore[index]
                # chapter range: e.g. Gn 37-45
                result.append(models.VerseRef(book, chapter, None, None, end[1]))  # type: ignore[index]
            else:
                result.append(models.VerseRef(book, chapter, start, end[2]))  # type: ignore[index]
            i += 3
        else:
            result.append(models.VerseRef(book, chapter, start, start))
            i += 1
    return result


def _get_footnote_map(soup: BeautifulSoup) -> dict[str, tuple[str, list[models.VerseRef]]]:
    """Builds a mapping from endnote anchor ID to (cleaned text, cross-references).

    Collects all ``<p class="en*">`` paragraphs that carry an ``id`` attribute.
    IDs follow the USCCB format ``BBCCCVVV-a`` (e.g. ``'01001001-a'``).
    Cross-references are extracted from ``/bible/`` anchor hrefs when present,
    falling back to text-based parsing otherwise.
    """
    result: dict[str, tuple[str, list[models.VerseRef]]] = {}
    for p in soup.find_all("p"):
        tag_p = cast("Tag", p)
        classes: list[str] = list(tag_p.get("class") or [])
        if not any(c.startswith("en") for c in classes):
            continue
        anchor_id = str(tag_p.get("id", ""))
        if not anchor_id:
            # Spanish format: id is on the inner <a class="ennum"> element
            ennum = tag_p.find("a", class_="ennum")
            if ennum:
                anchor_id = str(cast("Tag", ennum).get("id", ""))
        if anchor_id:
            raw_text = _clean_text(tag_p.get_text())
            refs = _parse_verse_refs_from_footnote_tag(tag_p)
            if not refs:
                refs = utils.parse_cross_references(raw_text)
            result[anchor_id] = (raw_text, refs)
    return result


def _iter_anchor_events(tag: Tag, classes: list[str]) -> Iterator[tuple[str, str]]:
    """Yields events from an ``<a>`` element.

    - ``enref`` anchors → ``("footnote_ref", anchor_id)``  (e.g. ``"01001001-a"``)
    - ``fnref`` anchors → skipped (cross-reference asterisks)
    - named verse anchors without a ``bcv``/``ver`` span → extract verse number from
      the 8-digit ``name`` attribute (``BBCCCVVV``), strip the leading digit(s) from text
    - all other anchors → recurse into children
    """
    if "enref" in classes:
        href = str(tag.get("href", "")).lstrip("#")  # e.g. "01001001-a"
        ref = tag.get_text(strip=True).strip("[]")  # e.g. "a"
        if ref and not ref.isdigit() and href:
            yield ("footnote_ref", href)
    elif "fnref" not in classes:
        name = str(tag.get("name", ""))
        if re.match(r"^\d{8}$", name) and not tag.find("span", class_="bcv") and not tag.find("span", class_="ver"):
            # Some books (e.g. 1 Chronicles) embed the verse number as leading digits
            # in the anchor text rather than using <span class="bcv">.
            # Extract the verse number from the BBCCCVVV name and strip it from the text.
            yield ("verse_num", str(int(name[5:])))
            for child in tag.children:
                if isinstance(child, NavigableString):
                    text = re.sub(r"^\d+", "", str(child))
                    if text.strip():
                        yield ("text", text)
                else:
                    yield from _iter_paragraph_events(cast("Tag", child))
        else:
            yield from _iter_paragraph_events(tag)


def _iter_paragraph_events(tag: Tag) -> Iterator[tuple[str, str]]:
    """Yields ``(event, value)`` pairs for all content within a paragraph element.

    Events:
      - ``"heading"``      — section heading text from ``<b>`` / ``<strong>``
      - ``"verse_num"``    — verse number string from ``<span class="bcv">``
      - ``"text"``         — plain verse text
      - ``"footnote_ref"`` — footnote letter from ``<a class="enref">``
    """
    for child in tag.children:
        if isinstance(child, NavigableString):
            if str(child).strip():
                yield ("text", str(child))
        else:
            child_tag = cast("Tag", child)
            child_name = child_tag.name  # type: ignore[attr-defined]
            child_classes = list(child_tag.get("class") or [])

            if child_name in ("b", "strong") or (child_name == "span" and "hemb" in child_classes):
                heading_text = child_tag.get_text(strip=True)
                if heading_text:
                    yield ("heading", heading_text)
            elif child_name == "span" and ("bcv" in child_classes or "ver" in child_classes):
                num = child_tag.get_text(strip=True)
                if num.isdigit():
                    yield ("verse_num", num)
            elif child_name == "a":
                yield from _iter_anchor_events(child_tag, child_classes)
            else:
                yield from _iter_paragraph_events(child_tag)


def _iter_section_events(paragraphs: Iterable[Tag]) -> Iterator[tuple[str, str]]:
    """Yields all content events from the chapter body, stopping at footnote paragraphs.

    ``<h2>`` and ``<h3>`` elements are emitted as ``("heading", ...)`` events directly.
    """
    for p in paragraphs:
        tag_p = cast("Tag", p)
        if any(c.startswith(("fn", "en")) for c in (tag_p.get("class") or [])):
            return
        if tag_p.name in ("h2", "h3"):
            texts = [v for ev, v in _iter_paragraph_events(tag_p) if ev == "text"]
            heading = _clean_text(" ".join(texts))
            if heading:
                yield ("heading", heading)
        else:
            yield from _iter_paragraph_events(tag_p)


class _SectionState:
    """Mutable accumulator used during a single chapter parse pass."""

    def __init__(self, footnote_map: dict[str, tuple[str, list[models.VerseRef]]]) -> None:
        self._footnote_map = footnote_map
        self.sections: list[models.BibleSection] = []
        self.heading: str | None = None
        self.verses: list[models.BibleVerse] = []
        self.verse_num: int | None = None
        self.texts: list[str] = []
        self.footnote_ids: list[str] = []

    def on_heading(self, value: str) -> None:
        self._flush_current_verse()
        if self.verses:
            self.sections.append(models.BibleSection(self.heading, self.verses))
            self.verses = []
        self.heading = value

    def on_verse_num(self, value: int) -> None:
        self._flush_current_verse()
        self.verse_num = value
        self.texts, self.footnote_ids = [], []

    def on_text(self, value: str) -> None:
        self.texts.append(value)

    def on_footnote_ref(self, value: str) -> None:
        self.footnote_ids.append(value)

    def _flush_current_verse(self) -> None:
        if self.verse_num is None:
            return
        verse_text = _clean_text(" ".join(self.texts))
        if verse_text:
            footnotes = []
            for anchor_id in self.footnote_ids:
                entry = self._footnote_map.get(anchor_id)
                if entry and entry[0]:
                    footnotes.append(models.BibleFootnote(_clean_footnote_text(entry[0]), entry[1]))
            self.verses.append(models.BibleVerse(self.verse_num, verse_text, footnotes))
        self.verse_num, self.texts, self.footnote_ids = None, [], []

    def finish(self) -> list[models.BibleSection]:
        self._flush_current_verse()
        if self.verses:
            self.sections.append(models.BibleSection(self.heading, self.verses))
        return self.sections


class USCCB:
    """Interface for querying Bible verses from https://bible.usccb.org/bible/"""

    def __init__(self) -> None:
        self._session: requests.AsyncSession[requests.Response] | None = None

    async def __aenter__(self) -> USCCB:  # noqa: PYI034
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Exit the async context manager, closing the underlying session."""
        await self.close()
        return False

    async def close(self) -> USCCB:
        """Closes the underlying connection."""
        if self._session is None:
            return self
        await self._session.close()
        return self

    async def get_chapter(
        self,
        book: str,
        chapter: int,
        language: models.Language = models.Language.ENGLISH,
    ) -> models.BibleChapter | None:
        """
        Fetches a single Bible chapter.

        Args:
            book (str): The book name, URL name, or abbreviation (e.g. 'genesis', 'Gen').
            chapter (int): The chapter number (1-based).
            language (Language): The language to fetch (default: ENGLISH).

        Returns:
            BibleChapter or None if the page could not be fetched.
        """
        url = self._build_url(book, chapter, language)
        book_info = utils.lookup_book(book)
        url_name = utils.book_url_name(book_info) if book_info else book.lower().replace(" ", "")
        return await self._get_chapter(url, url_name, chapter, language)

    async def get_book(
        self,
        book: str,
        language: models.Language = models.Language.ENGLISH,
        *,
        include_intro: bool = False,
    ) -> list[models.BibleChapter]:
        """
        Fetches all chapters of a Bible book concurrently.

        Args:
            book (str): The book name, URL name, or abbreviation (e.g. 'genesis', 'Gen').
            language (Language): The language to fetch (default: ENGLISH).
            include_intro (bool): If True, also fetch chapter 0 (the book introduction) and
                prepend it to the returned list (default: False).

        Returns:
            Ordered list of BibleChapter instances for each chapter of the book.
            When include_intro is True, chapter 0 (the introduction) is first.

        Raises:
            ValueError: If the book name is not recognised.
        """
        book_info = utils.lookup_book(book)
        if book_info is None:
            msg = f"Unknown book: {book!r}"
            raise ValueError(msg)

        first_chapter = 0 if include_intro else 1
        num_chapters = book_info.num_chapters
        tasks = [self.get_chapter(book, i, language) for i in range(first_chapter, num_chapters + 1)]
        results = await asyncio.gather(*tasks)
        chapters = [c for c in results if c is not None]
        chapters.sort(key=lambda c: c.number)
        return chapters

    async def get_verse_range(  # noqa: PLR0913
        self,
        book: str,
        start_chapter: int,
        start_verse: int,
        end_chapter: int,
        end_verse: int,
        language: models.Language = models.Language.ENGLISH,
    ) -> list[tuple[int, models.BibleVerse]]:
        """
        Fetches a range of verses spanning one or more chapters.

        Args:
            book (str): The book name, URL name, or abbreviation.
            start_chapter (int): The chapter number where the range begins.
            start_verse (int): The verse number where the range begins.
            end_chapter (int): The chapter number where the range ends.
            end_verse (int): The verse number where the range ends.
            language (Language): The language to fetch (default: ENGLISH).

        Returns:
            Ordered list of ``(chapter_number, BibleVerse)`` pairs covering the range.

        Raises:
            ValueError: If the end position is before the start position.
        """
        if end_chapter < start_chapter or (end_chapter == start_chapter and end_verse < start_verse):
            msg = f"End position {end_chapter}:{end_verse} is before start position {start_chapter}:{start_verse}"
            raise ValueError(msg)

        tasks = [self.get_chapter(book, ch, language) for ch in range(start_chapter, end_chapter + 1)]
        results = await asyncio.gather(*tasks)

        output: list[tuple[int, models.BibleVerse]] = []
        for chapter in sorted((c for c in results if c is not None), key=lambda c: c.number):
            for verse in chapter.verses:
                if chapter.number == start_chapter and verse.number < start_verse:
                    continue
                if chapter.number == end_chapter and verse.number > end_verse:
                    continue
                output.append((chapter.number, verse))
        return output

    async def get_verse(
        self,
        book: str,
        chapter: int,
        verse: int,
        language: models.Language = models.Language.ENGLISH,
    ) -> models.BibleVerse | None:
        """
        Fetches a single Bible verse.

        Args:
            book (str): The book name, URL name, or abbreviation.
            chapter (int): The chapter number.
            verse (int): The verse number.
            language (Language): The language to fetch (default: ENGLISH).

        Returns:
            BibleVerse or None if not found.
        """
        chapter_data = await self.get_chapter(book, chapter, language)
        if chapter_data is None:
            return None
        return chapter_data.get_verse(verse)

    def _build_url(self, book: str, chapter: int, language: models.Language) -> str:
        """Builds the USCCB URL for the given book/chapter/language."""
        book_info = utils.lookup_book(book)
        url_name = utils.book_url_name(book_info) if book_info else book.lower().replace(" ", "")
        prefix = language.url_prefix
        return constants.BIBLE_CHAPTER_URL_FMT.format(
            BASE=constants.BIBLE_BASE_URL,
            PREFIX=prefix,
            BOOK=url_name,
            CHAPTER=chapter,
        )

    async def _get_chapter(
        self,
        url: str,
        book: str,
        chapter: int,
        language: models.Language,
    ) -> models.BibleChapter | None:
        logger.info("Fetching chapter from url: %s", url)
        try:
            r = await self._ensure_session().get(url)
            r.raise_for_status()
            content = r.text
        except Exception:
            logger.info("Failed to fetch chapter from url: %s", url, exc_info=True)
            raise

        logger.info("Parsing chapter from url: %s", url)
        soup = BeautifulSoup(content, "html5lib")
        title_tag = cast("Tag", soup.find("title"))
        title = title_tag.get_text(strip=True).split("|")[0].strip() if title_tag else f"{book} {chapter}"
        sections = self._get_sections(soup, book, chapter)
        return models.BibleChapter(book, chapter, language, url, title, sections)

    def _get_sections(self, soup: BeautifulSoup, book: str, chapter: int) -> list[models.BibleSection]:
        """Parses all Bible sections (headings + verses) from the page."""
        chapter_heading = soup.find("div", class_="content")
        if chapter_heading is not None:
            paragraphs = cast("Tag", chapter_heading).find_all_next(["p", "h2", "h3"])
        else:
            logger.warning("Could not find chapter heading on page, parsing from document root.")
            root = cast("Tag", soup.find("main") or soup.find("body") or soup)
            paragraphs = root.find_all(["p", "h2", "h3"])

        footnote_map = _get_footnote_map(soup)
        state = _SectionState(footnote_map)
        for event, value in _iter_section_events(cast("list[Tag]", paragraphs)):
            if event == "heading":
                state.on_heading(value)
            elif event == "verse_num":
                state.on_verse_num(int(value))
            elif event == "text":
                state.on_text(value)
            elif event == "footnote_ref":
                state.on_footnote_ref(value)
        sections = state.finish()
        if not sections:
            logger.warning("No sections returned in %s:%d", book, chapter)
        return sections

    def _ensure_session(self) -> requests.AsyncSession[requests.Response]:
        if self._session is None:
            self._session = self._create_session()
        return self._session

    def _create_session(self) -> requests.AsyncSession[requests.Response]:
        return requests.AsyncSession(impersonate="chrome110")
