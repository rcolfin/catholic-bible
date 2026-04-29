from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from asyncclick.testing import CliRunner

from catholic_bible import models
from catholic_bible.commands.bible import _fetch_and_write_chapter
from catholic_bible.commands.common import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.asyncio
async def test_list_books_all(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["list-books"])
    assert result.exit_code == 0
    assert "Genesis" in result.output
    assert "Revelation" in result.output
    assert result.output.count("\n") == 73  # noqa: PLR2004


@pytest.mark.asyncio
async def test_list_books_old_testament(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["list-books", "old"])
    assert result.exit_code == 0
    assert "Genesis" in result.output
    assert "Malachi" in result.output
    assert "Matthew" not in result.output
    assert result.output.count("\n") == 46  # noqa: PLR2004


@pytest.mark.asyncio
async def test_list_books_new_testament(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["list-books", "new"])
    assert result.exit_code == 0
    assert "Matthew" in result.output
    assert "Revelation" in result.output
    assert "Genesis" not in result.output
    assert result.output.count("\n") == 27  # noqa: PLR2004


@pytest.mark.asyncio
async def test_list_books_case_insensitive(runner: CliRunner) -> None:
    result_lower = await runner.invoke(cli, ["list-books", "old"])
    result_upper = await runner.invoke(cli, ["list-books", "OLD"])
    assert result_lower.exit_code == 0
    assert result_upper.exit_code == 0
    assert result_lower.output == result_upper.output


@pytest.mark.asyncio
async def test_list_books_includes_chapter_count(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["list-books", "old"])
    assert "Genesis (50 chapters)" in result.output
    assert "Psalms (150 chapters)" in result.output


@pytest.mark.asyncio
async def test_get_book_save(runner: CliRunner, monkeypatch: Any, tmp_path: Path) -> None:
    chapter = models.BibleChapter(
        book="genesis",
        number=1,
        language=models.Language.ENGLISH,
        url="https://bible.usccb.org/bible/genesis/1",
        title="Genesis, Chapter 1",
        sections=[
            models.BibleSection(
                heading=None,
                verses=[models.BibleVerse(number=1, text="In the beginning...", footnotes=[])],
            )
        ],
    )

    with patch("catholic_bible.commands.bible.USCCB") as mock_usccb_cls:
        mock_usccb = AsyncMock()
        mock_usccb.get_book = AsyncMock(return_value=[chapter])
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb_cls.return_value = mock_usccb

        save_path = tmp_path / "genesis.json"
        result = await runner.invoke(cli, ["get-book", "--book", "genesis", "--save", str(save_path)])

    assert result.exit_code == 0
    assert save_path.exists()
    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["book"] == "genesis"
    assert data[0]["number"] == 1


@pytest.mark.asyncio
async def test_download_bible_requires_output_dir(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["download-bible"])
    assert result.exit_code != 0


def _make_chapter(book: str = "ruth", number: int = 1) -> models.BibleChapter:
    return models.BibleChapter(
        book=book,
        number=number,
        language=models.Language.ENGLISH,
        url=f"https://bible.usccb.org/bible/{book}/{number}",
        title=f"{book.title()}, Chapter {number}",
        sections=[models.BibleSection(heading=None, verses=[models.BibleVerse(number=1, text="text", footnotes=[])])],
    )


@pytest.mark.asyncio
async def test_fetch_and_write_chapter_success(tmp_path: Path) -> None:
    chapter = _make_chapter("ruth", 1)
    mock_usccb = AsyncMock()
    mock_usccb.get_chapter = AsyncMock(return_value=chapter)

    dest = tmp_path / "ruth" / "001.json"
    result = await _fetch_and_write_chapter(mock_usccb, "ruth", 1, models.Language.ENGLISH, dest)

    assert result is True
    assert dest.exists()


@pytest.mark.asyncio
async def test_fetch_and_write_chapter_none_non_intro(tmp_path: Path) -> None:
    mock_usccb = AsyncMock()
    mock_usccb.get_chapter = AsyncMock(return_value=None)

    dest = tmp_path / "ruth" / "001.json"
    result = await _fetch_and_write_chapter(mock_usccb, "ruth", 1, models.Language.ENGLISH, dest)

    assert result is False
    assert not dest.exists()


@pytest.mark.asyncio
async def test_fetch_and_write_chapter_none_intro_silent(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Chapter 0 returning None should be silent (no warning), not counted as error."""
    mock_usccb = AsyncMock()
    mock_usccb.get_chapter = AsyncMock(return_value=None)

    dest = tmp_path / "ruth" / "000.json"
    with caplog.at_level(logging.WARNING, logger="catholic_bible.commands.bible"):
        result = await _fetch_and_write_chapter(mock_usccb, "ruth", 0, models.Language.ENGLISH, dest)

    assert result is False
    assert not dest.exists()
    assert caplog.records == []


@pytest.mark.asyncio
async def test_download_bible_by_chapter(runner: CliRunner, tmp_path: Path) -> None:
    """By-chapter mode writes one file per chapter under <book_slug>/NNN.json."""
    # Ruth has 4 chapters — small enough for a fast test
    chapters = [_make_chapter("ruth", n) for n in range(1, 5)]

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(
            side_effect=lambda book, ch, lang: next((c for c in chapters if c.number == ch), None)
        )
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(
            cli,
            [
                "download-bible",
                "--output-dir",
                str(tmp_path),
                "--testament",
                "old",
                "--no-skip-existing",
                "--concurrency",
                "1",
            ],
        )

    assert result.exit_code == 0
    ruth_dir = tmp_path / "ruth"
    assert ruth_dir.is_dir()
    for n in range(1, 5):
        assert (ruth_dir / f"{n:03d}.json").exists(), f"Missing ruth/{n:03d}.json"
    assert "Downloaded" in result.output


@pytest.mark.asyncio
async def test_download_bible_by_book(runner: CliRunner, tmp_path: Path) -> None:
    """By-book mode writes one JSON file per book at <book_slug>.json."""
    chapters = [_make_chapter("ruth", n) for n in range(1, 5)]

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_book = AsyncMock(return_value=chapters)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(
            cli,
            [
                "download-bible",
                "--output-dir",
                str(tmp_path),
                "--testament",
                "old",
                "--by-book",
                "--no-skip-existing",
                "--concurrency",
                "1",
            ],
        )

    assert result.exit_code == 0
    ruth_file = tmp_path / "ruth.json"
    assert ruth_file.exists()
    data = json.loads(ruth_file.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 4  # noqa: PLR2004
    assert data[0]["book"] == "ruth"


@pytest.mark.asyncio
async def test_download_bible_skip_existing_chapter(runner: CliRunner, tmp_path: Path) -> None:
    """By-chapter: chapters whose file already exists are not re-fetched."""
    # Pre-create chapters 1 and 2 for Ruth (4 chapters total)
    ruth_dir = tmp_path / "ruth"
    ruth_dir.mkdir()
    for n in (1, 2):
        (ruth_dir / f"{n:03d}.json").write_text(json.dumps({"pre": "existing"}), encoding="utf-8")

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(return_value=_make_chapter("ruth", 3))
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(
            cli,
            [
                "download-bible",
                "--output-dir",
                str(tmp_path),
                "--testament",
                "old",
                "--skip-existing",
                "--concurrency",
                "1",
            ],
        )

    assert result.exit_code == 0
    # Only Ruth chapters 3 and 4 should be fetched (filter to Ruth to avoid noise from other OT books)
    ruth_calls = [call.args[1] for call in mock_usccb.get_chapter.call_args_list if call.args[0] == "ruth"]
    assert 1 not in ruth_calls
    assert 2 not in ruth_calls  # noqa: PLR2004
    assert 3 in ruth_calls  # noqa: PLR2004
    assert 4 in ruth_calls  # noqa: PLR2004


@pytest.mark.asyncio
async def test_download_bible_skip_existing_book(runner: CliRunner, tmp_path: Path) -> None:
    """By-book: books whose file already exists are not re-fetched."""
    (tmp_path / "ruth.json").write_text(json.dumps([]), encoding="utf-8")

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_book = AsyncMock(return_value=[])
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(
            cli,
            [
                "download-bible",
                "--output-dir",
                str(tmp_path),
                "--testament",
                "old",
                "--by-book",
                "--skip-existing",
                "--concurrency",
                "1",
            ],
        )

    assert result.exit_code == 0
    # Ruth's get_book should never be called
    ruth_calls = [c for c in mock_usccb.get_book.call_args_list if c.args[0] == "ruth"]
    assert not ruth_calls


@pytest.mark.asyncio
async def test_download_bible_all_chapters_exist_counts_as_skipped(runner: CliRunner, tmp_path: Path) -> None:
    """By-chapter: book with all chapter files present counts as Skipped in summary."""
    ruth_dir = tmp_path / "ruth"
    ruth_dir.mkdir()
    for n in range(1, 5):  # Ruth has 4 chapters
        (ruth_dir / f"{n:03d}.json").write_text(json.dumps({}), encoding="utf-8")

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        # Return None for all chapters so other OT books don't cause JSON-serialization errors
        mock_usccb.get_chapter = AsyncMock(return_value=None)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(
            cli,
            [
                "download-bible",
                "--output-dir",
                str(tmp_path),
                "--testament",
                "old",
                "--skip-existing",
                "--concurrency",
                "1",
            ],
        )

    assert result.exit_code == 0
    assert "1 books skipped" in result.output
    # Ruth's chapters were never fetched (all existed)
    ruth_calls = [c for c in mock_usccb.get_chapter.call_args_list if c.args[0] == "ruth"]
    assert not ruth_calls


class TestCLIErrorHandling:
    """Tests for error handling in CLI commands with invalid book names."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @pytest.mark.asyncio
    async def test_get_chapter_invalid_book_shows_suggestion(
        self, runner: CliRunner, caplog: pytest.LogCaptureFixture
    ) -> None:
        """get-chapter with typo should show closest match."""
        result = await runner.invoke(cli, ["get-chapter", "--book", "corinthians", "--chapter", "1"])
        assert result.exit_code == 1
        assert "Book 'corinthians' not found" in caplog.text
        assert "Did you mean:" in caplog.text
        # Should suggest 1 Corinthians or 2 Corinthians
        assert "Corinthians" in caplog.text

    @pytest.mark.asyncio
    async def test_get_chapter_invalid_book_no_match(self, runner: CliRunner, caplog: pytest.LogCaptureFixture) -> None:
        """get-chapter with very wrong book name should show generic error."""
        result = await runner.invoke(cli, ["get-chapter", "--book", "xyz", "--chapter", "1"])
        assert result.exit_code == 1
        assert "Book 'xyz' not found" in caplog.text

    @pytest.mark.asyncio
    async def test_get_verse_invalid_book(self, runner: CliRunner, caplog: pytest.LogCaptureFixture) -> None:
        """get-verse with invalid book should show error."""
        result = await runner.invoke(cli, ["get-verse", "--book", "invalid", "--chapter", "1", "--verse", "1"])
        assert result.exit_code == 1
        assert "Book 'invalid' not found" in caplog.text

    @pytest.mark.asyncio
    async def test_get_book_invalid_book(self, runner: CliRunner, caplog: pytest.LogCaptureFixture) -> None:
        """get-book with invalid book should show error."""
        result = await runner.invoke(cli, ["get-book", "--book", "notabook"])
        assert result.exit_code == 1
        assert "Book 'notabook' not found" in caplog.text

    @pytest.mark.asyncio
    async def test_get_chapter_valid_book_still_works(self, runner: CliRunner) -> None:
        """get-chapter with valid book should work."""
        with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
            mock_usccb = AsyncMock()
            mock_usccb.get_chapter = AsyncMock(return_value=None)
            mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
            mock_usccb.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_usccb

            result = await runner.invoke(cli, ["get-chapter", "--book", "Genesis", "--chapter", "1"])
        # Should not fail due to error handling
        # Exit code might be 0 or non-zero depending on mock, just not treated as input error
        assert "Book 'Genesis' not found" not in result.output
