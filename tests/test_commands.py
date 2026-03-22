from __future__ import annotations

import pytest
from asyncclick.testing import CliRunner

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
    result = await runner.invoke(cli, ["list-books", "--testament", "old"])
    assert result.exit_code == 0
    assert "Genesis" in result.output
    assert "Malachi" in result.output
    assert "Matthew" not in result.output
    assert result.output.count("\n") == 46  # noqa: PLR2004


@pytest.mark.asyncio
async def test_list_books_new_testament(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["list-books", "--testament", "new"])
    assert result.exit_code == 0
    assert "Matthew" in result.output
    assert "Revelation" in result.output
    assert "Genesis" not in result.output
    assert result.output.count("\n") == 27  # noqa: PLR2004


@pytest.mark.asyncio
async def test_list_books_case_insensitive(runner: CliRunner) -> None:
    result_lower = await runner.invoke(cli, ["list-books", "--testament", "old"])
    result_upper = await runner.invoke(cli, ["list-books", "--testament", "OLD"])
    assert result_lower.exit_code == 0
    assert result_upper.exit_code == 0
    assert result_lower.output == result_upper.output


@pytest.mark.asyncio
async def test_list_books_includes_chapter_count(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["list-books", "--testament", "old"])
    assert "Genesis (50 chapters)" in result.output
    assert "Psalms (150 chapters)" in result.output
