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

    monkeypatch.setattr(requests.AsyncSession, "get", mock_async_get)


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
async def test_get_chapter_footnotes(monkeypatch: Any) -> None:
    """Tests that footnotes are captured with ref letter and text in verse 1."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, models.Language.ENGLISH)

    assert chapter is not None
    verse_1 = chapter.get_verse(1)
    assert verse_1 is not None
    assert len(verse_1.footnotes) == 1
    assert "Gn 2:1" in verse_1.footnotes[0].text


@pytest.mark.asyncio
async def test_get_chapter_footnote_cross_references(monkeypatch: Any) -> None:
    """Tests that a cross-reference footnote produces structured VerseRef objects."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, models.Language.ENGLISH)

    assert chapter is not None
    verse_3 = chapter.get_verse(3)
    assert verse_3 is not None
    assert len(verse_3.footnotes) == 1
    fn = verse_3.footnotes[0]
    assert len(fn.cross_references) == 1
    assert fn.cross_references[0].to_dict() == {"book": "2corinthians", "chapter": 4, "start_verse": 6, "end_verse": 6}


@pytest.mark.asyncio
async def test_get_chapter_section_headings(monkeypatch: Any) -> None:
    """Tests that section headings are parsed correctly."""
    html_path = DATA_PATH / "genesis-chapter-1.html"
    _setup_mock(monkeypatch, html_path)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, models.Language.ENGLISH)

    assert chapter is not None
    assert len(chapter.sections) == 1
    assert chapter.sections[0].heading == "The Story of Creation."


@pytest.mark.asyncio
async def test_get_chapter_no_chapter_heading(monkeypatch: Any) -> None:
    """Tests that verses are still parsed when the chapter <h3> heading is absent."""
    html = (
        "<html><head><title>Obadiah, Chapter 1 | USCCB</title></head>"
        "<body><main>"
        '<p class="pf"><a name="31001001"><span class="bcv">1</span>A vision of Obadiah.</a></p>'
        '<p class="en" id="31001001-a">a. [1:1] A note.</p>'
        "</main></body></html>"
    )

    class MockResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            pass

    async def mock_get(self: Any, url: str) -> MockResponse:
        return MockResponse(html)

    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("obadiah", 1, models.Language.ENGLISH)

    assert chapter is not None
    assert len(chapter.sections) == 1
    assert chapter.sections[0].verses[0].number == 1
    assert "Obadiah" in chapter.sections[0].verses[0].text


@pytest.mark.asyncio
async def test_get_chapter_spanish_structure(monkeypatch: Any) -> None:
    """Tests parsing of the Spanish USCCB HTML structure (h1.cn, span.ver, span.hemb, inline ennum)."""
    html = (
        "<html><head><title>Mateo, Capítulo 2 | USCCB</title></head>"
        "<body><main>"
        '<h1 class="cn"><a href="#">Capítulo 2</a></h1>'
        '<p class="pf">'
        '<span class="hemb">Visita de los magos.</span> '
        '<span class="ver" id="v40002001">1</span>'
        '<a class="enref" href="#en40002001" id="ren40002001">a</a>'
        "Después del nacimiento de Jesús en Belén de Judea,"
        "</p>"
        '<p class="fn">* [2:1] A cross-reference note.</p>'
        '<p class="en">'
        '<a class="ennum" href="#ren40002001" id="en40002001">a.</a>'
        " 2:1: Lc 2:1-7."
        "</p>"
        "</main></body></html>"
    )

    class MockResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            pass

    async def mock_get(self: Any, url: str) -> MockResponse:
        return MockResponse(html)

    monkeypatch.setattr(requests.AsyncSession, "get", mock_get)

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("matthew", 2, models.Language.SPANISH)

    assert chapter is not None
    assert len(chapter.sections) == 1
    assert chapter.sections[0].heading == "Visita de los magos."
    verse_1 = chapter.get_verse(1)
    assert verse_1 is not None
    assert "Belén" in verse_1.text
    assert len(verse_1.footnotes) == 1
    assert "Lc 2:1" in verse_1.footnotes[0].text


@pytest.mark.asyncio
async def test_get_chapter_inline_verse_numbers(monkeypatch: Any) -> None:
    """Tests parsing when verse numbers are leading digits in anchor text, not in bcv spans (1Chronicles style)."""
    html = (
        "<html><head><title>1 Chronicles, Chapter 1 | USCCB</title></head>"
        '<body><div class="content">'
        "<h2>I. GENEALOGICAL TABLES</h2>"
        '<p class="pf"><strong>From Adam to Abraham.</strong> '
        '<a name="13001001">1Adam, Seth, Enosh,</a>'
        '<a class="enref" href="#13001001-a"><sup>a</sup></a> '
        '<a name="13001002">2Kenan, Mahalalel, Jared.</a></p>'
        '<p><a name="13001008">8The sons of Ham were Cush.</a></p>'
        '<p class="en" id="13001001-a">a. [1:1] Gn 5:3.</p>'
        "</div></body></html>"
    )
    monkeypatch.setattr(requests.AsyncSession, "get", _make_mock_response(html))

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("1chronicles", 1, models.Language.ENGLISH)

    assert chapter is not None
    verse_1 = chapter.get_verse(1)
    assert verse_1 is not None
    assert "Adam" in verse_1.text
    verse_2 = chapter.get_verse(2)
    assert verse_2 is not None
    assert "Kenan" in verse_2.text
    verse_8 = chapter.get_verse(8)
    assert verse_8 is not None
    assert "Ham" in verse_8.text


@pytest.mark.asyncio
async def test_get_chapter_h2_section_heading(monkeypatch: Any) -> None:
    """Tests that <h2> section headings are captured when no <strong> heading follows in the same section."""
    html = (
        "<html><head><title>1 Chronicles, Chapter 1 | USCCB</title></head>"
        '<body><div class="content">'
        "<h2>I. GENEALOGICAL TABLES</h2>"
        '<p><a name="13001001"><span class="bcv">1</span>Adam, Seth, Enosh.</a></p>'
        "</div></body></html>"
    )
    monkeypatch.setattr(requests.AsyncSession, "get", _make_mock_response(html))

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("1chronicles", 1, models.Language.ENGLISH)

    assert chapter is not None
    assert len(chapter.sections) == 1
    assert chapter.sections[0].heading == "I. GENEALOGICAL TABLES"
    assert chapter.get_verse(1) is not None


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


def _make_mock_response(html: str) -> Any:
    class MockResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            pass

    async def mock_get(self: Any, url: str) -> MockResponse:
        return MockResponse(html)

    return mock_get


@pytest.mark.asyncio
async def test_footnote_cross_ref_from_href_single(monkeypatch: Any) -> None:
    """Tests that a footnote with a /bible/ href anchor produces a VerseRef from the href."""
    html = (
        "<html><head><title>Deuteronomy, Chapter 8 | USCCB</title></head>"
        '<body><div class="content">'
        '<p><a name="05008017"><span class="bcv">17</span>verse text</a>'
        '<a class="enref" href="#05008017-a"><sup>a</sup></a></p>'
        '<p class="en" id="05008017-a">a. [8:17] '
        '<a href="/bible/deuteronomy/8?17">Dt 8:17f</a>.</p>'
        "</div></body></html>"
    )
    monkeypatch.setattr(requests.AsyncSession, "get", _make_mock_response(html))

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("deuteronomy", 8, models.Language.ENGLISH)

    assert chapter is not None
    verse = chapter.get_verse(17)
    assert verse is not None
    assert len(verse.footnotes) == 1
    fn = verse.footnotes[0]
    assert len(fn.cross_references) == 1
    assert fn.cross_references[0].to_dict() == {"book": "deuteronomy", "chapter": 8, "start_verse": 17, "end_verse": 17}


@pytest.mark.asyncio
async def test_footnote_cross_ref_from_href_range_with_bracket_prefix(monkeypatch: Any) -> None:
    """Tests a footnote with bracketed source context and an href-based range cross-reference."""
    html = (
        "<html><head><title>Psalms, Chapter 44 | USCCB</title></head>"
        '<body><div class="content">'
        '<p><a name="23044010"><span class="bcv">10</span>verse text</a>'
        '<a class="enref" href="#23044010-f"><sup>f</sup></a></p>'
        '<p class="en wv" id="23044010-f">f. ['
        '<a href="/bible/psalms/44?10">44:10</a>'
        "\u2013"
        '<a href="/bible/psalms/44?27">27</a>'
        '] <a href="/bible/psalms/89?39">Ps 89:39</a>'
        "\u2013"
        '<a href="/bible/psalms/89?52">52</a>.</p>'
        "</div></body></html>"
    )
    monkeypatch.setattr(requests.AsyncSession, "get", _make_mock_response(html))

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("psalms", 44, models.Language.ENGLISH)

    assert chapter is not None
    verse = chapter.get_verse(10)
    assert verse is not None
    assert len(verse.footnotes) == 1
    fn = verse.footnotes[0]
    assert len(fn.cross_references) == 1
    assert fn.cross_references[0].to_dict() == {"book": "psalms", "chapter": 89, "start_verse": 39, "end_verse": 52}


@pytest.mark.asyncio
async def test_footnote_cross_ref_from_absolute_href_multiple(monkeypatch: Any) -> None:
    """Tests footnote parsing with full https://bible.usccb.org hrefs and semicolon-separated refs."""
    html = (
        "<html><head><title>Isaiah, Chapter 5 | USCCB</title></head>"
        '<body><div class="content">'
        '<p><a name="29005025"><span class="bcv">25</span>verse text</a>'
        '<a class="enref" href="#29005025-p"><sup>p</sup></a></p>'
        '<p class="en wv" id="29005025-p">p. ['
        '<a href="https://bible.usccb.org/bible/is/5?25#29005025">5:25</a>'
        '] <a href="https://bible.usccb.org/bible/am/1?1#38001001">Am 1:1</a>'
        '; <a href="https://bible.usccb.org/bible/zec/14?5#46014005">Zec 14:5</a>'
        '; cf. <a href="https://bible.usccb.org/bible/is/9?18#29009018">Is 9:18a</a>.</p>'
        "</div></body></html>"
    )
    monkeypatch.setattr(requests.AsyncSession, "get", _make_mock_response(html))

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("isaiah", 5, models.Language.ENGLISH)

    assert chapter is not None
    verse = chapter.get_verse(25)
    assert verse is not None
    fn = verse.footnotes[0]
    assert len(fn.cross_references) == 3  # noqa: PLR2004
    assert fn.cross_references[0].to_dict() == {"book": "amos", "chapter": 1, "start_verse": 1, "end_verse": 1}
    assert fn.cross_references[1].to_dict() == {"book": "zechariah", "chapter": 14, "start_verse": 5, "end_verse": 5}
    assert fn.cross_references[2].to_dict() == {"book": "isaiah", "chapter": 9, "start_verse": 18, "end_verse": 18}


@pytest.mark.asyncio
async def test_footnote_cross_ref_from_href_chapter_only(monkeypatch: Any) -> None:
    """Tests that a chapter-only href (empty query) produces a chapter-only VerseRef."""
    html = (
        "<html><head><title>Wisdom, Chapter 10 | USCCB</title></head>"
        '<body><div class="content">'
        '<p><a name="27010013"><span class="bcv">13</span>verse text</a>'
        '<a class="enref" href="#27010013-m"><sup>m</sup></a></p>'
        '<p class="en" id="27010013-m">m. ['
        '<a href="https://bible.usccb.org/bible/wis/10?13#27010013">10:13</a>'
        "\u2013"
        '<a href="https://bible.usccb.org/bible/wis/10?14#27010014">14</a>'
        '] <a href="https://bible.usccb.org/bible/gn/37?#01037000">Gn 37</a>'
        "\u2013"
        '<a href="https://bible.usccb.org/bible/gn/45?#01045000">45</a>.</p>'
        "</div></body></html>"
    )
    monkeypatch.setattr(requests.AsyncSession, "get", _make_mock_response(html))

    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("wisdom", 10, models.Language.ENGLISH)

    assert chapter is not None
    verse = chapter.get_verse(13)
    assert verse is not None
    fn = verse.footnotes[0]
    assert len(fn.cross_references) == 1
    assert fn.cross_references[0].to_dict() == {"book": "genesis", "chapter": 37, "end_chapter": 45}
