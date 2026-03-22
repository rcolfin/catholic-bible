from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import pytest
from curl_cffi import requests

from catholic_bible import USCCB, models

DATA_PATH: Final[Path] = Path(__file__).parent / "data"


def _setup_mock(monkeypatch: Any, html_path: Path) -> None:
    class MockResponse:
        def __init__(self, text: str) -> None:
            self.text = text
            self.status_code = 200

        def raise_for_status(self: MockResponse) -> None:
            pass

    async def mock_async_get(self: requests.AsyncSession[requests.Response], url: str) -> MockResponse:
        html_content = html_path.read_text(encoding="utf-8")  # noqa: ASYNC240
        return MockResponse(html_content)

    monkeypatch.setattr(requests.AsyncSession[requests.Response], "get", mock_async_get)


@pytest.mark.asyncio
async def test_get_chapter_parse(monkeypatch: Any) -> None:
    """Tests parsing a Genesis chapter 1 page."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    json_path = DATA_PATH / "genesis-chapter-1.json"
    expected = json.loads(json_path.read_text(encoding="utf-8"))

    _setup_mock(monkeypatch, html_path)
    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, models.Language.ENGLISH)

    assert chapter is not None
    assert expected == chapter.to_dict()


@pytest.mark.asyncio
async def test_get_verse(monkeypatch: Any) -> None:
    """Tests fetching a single verse from a chapter."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        verse = await usccb.get_verse("genesis", 1, 3, models.Language.ENGLISH)

    assert verse is not None
    assert verse.number == 3  # noqa: PLR2004
    assert "light" in verse.text


@pytest.mark.asyncio
async def test_get_verse_not_found(monkeypatch: Any) -> None:
    """Tests that get_verse returns None for a non-existent verse number."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        verse = await usccb.get_verse("genesis", 1, 999, models.Language.ENGLISH)

    assert verse is None


@pytest.mark.asyncio
async def test_get_chapter_footnote_refs(monkeypatch: Any) -> None:
    """Tests that footnote references are captured in verse 1."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, models.Language.ENGLISH)

    assert chapter is not None
    verse_1 = chapter.get_verse(1)
    assert verse_1 is not None
    assert "a" in verse_1.footnote_refs


@pytest.mark.asyncio
async def test_get_chapter_section_headings(monkeypatch: Any) -> None:
    """Tests that section headings are parsed correctly."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, models.Language.ENGLISH)

    assert chapter is not None
    assert len(chapter.sections) == 2  # noqa: PLR2004
    assert chapter.sections[0].heading == "The Story of Creation."
    assert chapter.sections[1].heading == "The Second Day."


def test_usccb_build_url_english() -> None:
    usccb = USCCB()
    url = usccb._build_url("genesis", 1, models.Language.ENGLISH)  # noqa: SLF001
    assert url == "https://bible.usccb.org/bible/genesis/1"


def test_usccb_build_url_spanish() -> None:
    usccb = USCCB()
    url = usccb._build_url("genesis", 1, models.Language.SPANISH)  # noqa: SLF001
    assert url == "https://bible.usccb.org/es/bible/genesis/1"


def test_usccb_build_url_abbreviation() -> None:
    usccb = USCCB()
    url = usccb._build_url("Gen", 5, models.Language.ENGLISH)  # noqa: SLF001
    assert url == "https://bible.usccb.org/bible/genesis/5"


def test_usccb_build_url_numbered_book() -> None:
    usccb = USCCB()
    url = usccb._build_url("1corinthians", 1, models.Language.ENGLISH)  # noqa: SLF001
    assert url == "https://bible.usccb.org/bible/1corinthians/1"


def test_usccb_build_url_multi_word_book() -> None:
    usccb = USCCB()
    url = usccb._build_url("Song of Songs", 1, models.Language.ENGLISH)  # noqa: SLF001
    assert url == "https://bible.usccb.org/bible/songofsongs/1"


@pytest.mark.asyncio
async def test_get_book_unknown_raises() -> None:
    """Tests that get_book raises ValueError for an unknown book name."""
    async with USCCB() as usccb:
        with pytest.raises(ValueError, match="Unknown book"):
            await usccb.get_book("notabook")


@pytest.mark.asyncio
async def test_get_book_single_chapter(monkeypatch: Any) -> None:
    """Tests get_book with Obadiah, which has only 1 chapter."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        chapters = await usccb.get_book("obadiah")

    assert len(chapters) == 1
    assert chapters[0].number == 1
    assert chapters[0].book == "obadiah"


@pytest.mark.asyncio
async def test_get_chapter_spanish_url(monkeypatch: Any) -> None:
    """Tests that Spanish language uses the correct URL prefix."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, models.Language.SPANISH)

    assert chapter is not None
    assert chapter.language == models.Language.SPANISH
    assert "es/bible" in chapter.url
