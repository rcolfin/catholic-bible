from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import asyncclick as click

from catholic_bible import USCCB, _io, constants, models
from catholic_bible.commands.common import cli

logger = logging.getLogger(__name__)

_LANGUAGES: Final[list[str]] = [lang.name for lang in models.Language]


def _get_language(_ctx: click.Context, _param: click.Option, value: str) -> models.Language:
    return models.Language(value)


@cli.command("get-chapter")
@click.option("--book", required=True, help="Book name, URL name, or abbreviation (e.g. 'genesis', 'Gen').")
@click.option("--chapter", required=True, type=int, help="Chapter number (1-based).")
@click.option(
    "--language",
    type=click.Choice(_LANGUAGES, case_sensitive=False),
    default="ENGLISH",
    show_default=True,
    callback=_get_language,
    help="Bible language.",
)
@click.option("--save", type=click.Path(dir_okay=False, writable=True), help="Save output to this JSON file.")
async def get_chapter(
    book: str,
    chapter: int,
    language: models.Language,
    save: str | None,
) -> None:
    """Fetch a single Bible chapter and print it to stdout."""
    async with USCCB() as usccb:
        result = await usccb.get_chapter(book, chapter, language)
        if result is None:
            logger.error("Failed to retrieve %s chapter %d (%s)", book, chapter, language.name)
            return

    print(result)  # noqa: T201

    if save is not None:
        await _io.write_file(Path(save), result.to_dict())


@cli.command("get-verse")
@click.option("--book", required=True, help="Book name, URL name, or abbreviation.")
@click.option("--chapter", required=True, type=int, help="Chapter number (1-based).")
@click.option("--verse", required=True, type=int, help="Verse number.")
@click.option(
    "--language",
    type=click.Choice(_LANGUAGES, case_sensitive=False),
    default="ENGLISH",
    show_default=True,
    callback=_get_language,
    help="Bible language.",
)
async def get_verse(
    book: str,
    chapter: int,
    verse: int,
    language: models.Language,
) -> None:
    """Fetch a single Bible verse and print it to stdout."""
    async with USCCB() as usccb:
        result = await usccb.get_verse(book, chapter, verse, language)
        if result is None:
            logger.error("Verse not found: %s %d:%d (%s)", book, chapter, verse, language.name)
            return

    print(result)  # noqa: T201


@cli.command("get-book")
@click.option("--book", required=True, help="Book name, URL name, or abbreviation.")
@click.option(
    "--language",
    type=click.Choice(_LANGUAGES, case_sensitive=False),
    default="ENGLISH",
    show_default=True,
    callback=_get_language,
    help="Bible language.",
)
@click.option(
    "--save-dir",
    type=click.Path(file_okay=False, writable=True),
    help="Directory to save each chapter as a separate JSON file.",
)
async def get_book(
    book: str,
    language: models.Language,
    save_dir: str | None,
) -> None:
    """Fetch all chapters of a Bible book and print them to stdout."""
    async with USCCB() as usccb:
        chapters = await usccb.get_book(book, language)

    if not chapters:
        logger.error("No chapters retrieved for %s (%s)", book, language.name)
        return

    for chapter in chapters:
        print(chapter)  # noqa: T201

    if save_dir is not None:
        save_path = Path(save_dir)
        for chapter in chapters:
            file_path = save_path / f"{chapter.book}-{chapter.number:04d}.json"
            await _io.write_file(file_path, chapter.to_dict())


_TESTAMENT_CHOICES: Final[list[str]] = ["old", "new"]


@cli.command("list-books")
@click.option(
    "--testament",
    type=click.Choice(_TESTAMENT_CHOICES, case_sensitive=False),
    default=None,
    help="Filter by testament: 'old' or 'new'. Omit to list all 73 books.",
)
async def list_books(testament: str | None) -> None:
    """List Bible books with their chapter counts."""
    if testament is None:
        books = constants.ALL_BOOKS
    elif testament.lower() == "old":
        books = list(constants.OLD_TESTAMENT_BOOKS)
    else:
        books = list(constants.NEW_TESTAMENT_BOOKS)

    for book in books:
        print(f"{book.name} ({book.num_chapters} chapters)")  # noqa: T201
