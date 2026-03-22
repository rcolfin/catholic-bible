from __future__ import annotations

import asyncio
import html
import logging
import re
from typing import TYPE_CHECKING, Final, cast

from bs4 import BeautifulSoup, NavigableString
from curl_cffi import requests

from catholic_bible import constants, models, utils

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType

    from bs4.element import Tag

logger = logging.getLogger(__name__)

_CHAPTER_HEADING_PATTERN: Final[re.Pattern[str]] = re.compile(r"chapter", re.IGNORECASE)


def _clean_text(text: str) -> str:
    """Normalises whitespace and unescapes HTML entities in verse text."""
    text = html.unescape(text.replace("\xa0", " "))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _iter_anchor_events(tag: Tag, classes: list[str]) -> Iterator[tuple[str, str]]:
    """Yields events from an ``<a>`` element.

    - ``enref`` anchors → ``("footnote_ref", letter)``
    - ``fnref`` anchors → skipped (cross-reference asterisks)
    - named anchors    → recurse into children
    """
    if "enref" in classes:
        ref = tag.get_text(strip=True).strip("[]")
        if ref and not ref.isdigit():
            yield ("footnote_ref", ref)
    elif "fnref" not in classes:
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

            if child_name in ("b", "strong"):
                heading_text = child_tag.get_text(strip=True)
                if heading_text:
                    yield ("heading", heading_text)
            elif child_name == "span" and "bcv" in child_classes:
                num = child_tag.get_text(strip=True)
                if num.isdigit():
                    yield ("verse_num", num)
            elif child_name == "a":
                yield from _iter_anchor_events(child_tag, child_classes)
            else:
                yield from _iter_paragraph_events(child_tag)


def _iter_section_events(chapter_h3: Tag) -> Iterator[tuple[str, str]]:
    """Yields all content events from the chapter body, stopping at footnote paragraphs."""
    for p in chapter_h3.find_all_next("p"):
        tag_p = cast("Tag", p)
        if any(c.startswith("fn") for c in (tag_p.get("class") or [])):
            return
        yield from _iter_paragraph_events(tag_p)


class _SectionState:
    """Mutable accumulator used during a single chapter parse pass."""

    def __init__(self) -> None:
        self.sections: list[models.BibleSection] = []
        self.heading: str | None = None
        self.verses: list[models.BibleVerse] = []
        self.verse_num: int | None = None
        self.texts: list[str] = []
        self.footnotes: list[str] = []

    def on_heading(self, value: str) -> None:
        self._flush_current_verse()
        if self.verses:
            self.sections.append(models.BibleSection(self.heading, self.verses))
            self.verses = []
        self.heading = value

    def on_verse_num(self, value: int) -> None:
        self._flush_current_verse()
        self.verse_num = value
        self.texts, self.footnotes = [], []

    def on_text(self, value: str) -> None:
        self.texts.append(value)

    def on_footnote_ref(self, value: str) -> None:
        self.footnotes.append(value)

    def _flush_current_verse(self) -> None:
        if self.verse_num is None:
            return
        verse_text = _clean_text(" ".join(self.texts))
        if verse_text:
            self.verses.append(models.BibleVerse(self.verse_num, verse_text, list(self.footnotes)))
        self.verse_num, self.texts, self.footnotes = None, [], []

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
    ) -> list[models.BibleChapter]:
        """
        Fetches all chapters of a Bible book concurrently.

        Args:
            book (str): The book name, URL name, or abbreviation (e.g. 'genesis', 'Gen').
            language (Language): The language to fetch (default: ENGLISH).

        Returns:
            Ordered list of BibleChapter instances for each chapter of the book.

        Raises:
            ValueError: If the book name is not recognised.
        """
        book_info = utils.lookup_book(book)
        if book_info is None:
            msg = f"Unknown book: {book!r}"
            raise ValueError(msg)

        num_chapters = book_info.num_chapters
        tasks = [self.get_chapter(book, i, language) for i in range(1, num_chapters + 1)]
        results = await asyncio.gather(*tasks)
        chapters = [c for c in results if c is not None]
        chapters.sort(key=lambda c: c.number)
        return chapters

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
        sections = self._get_sections(soup)
        return models.BibleChapter(book, chapter, language, url, title, sections)

    def _get_sections(self, soup: BeautifulSoup) -> list[models.BibleSection]:
        """Parses all Bible sections (headings + verses) from the page."""
        chapter_h3 = soup.find("h3", string=_CHAPTER_HEADING_PATTERN)
        if chapter_h3 is None:
            logger.warning("Could not find chapter heading on page.")
            return []

        state = _SectionState()
        for event, value in _iter_section_events(cast("Tag", chapter_h3)):
            if event == "heading":
                state.on_heading(value)
            elif event == "verse_num":
                state.on_verse_num(int(value))
            elif event == "text":
                state.on_text(value)
            elif event == "footnote_ref":
                state.on_footnote_ref(value)
        return state.finish()

    def _ensure_session(self) -> requests.AsyncSession[requests.Response]:
        if self._session is None:
            self._session = self._create_session()
        return self._session

    def _create_session(self) -> requests.AsyncSession[requests.Response]:
        return requests.AsyncSession[requests.Response](impersonate="chrome110")
