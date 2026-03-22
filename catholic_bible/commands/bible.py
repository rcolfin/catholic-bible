from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Final

import asyncclick as click

from catholic_bible import USCCB, _io, constants, models, utils
from catholic_bible.commands.common import cli

logger = logging.getLogger(__name__)

_LANGUAGES: Final[list[str]] = [lang.name for lang in models.Language]
_TESTAMENTS: Final[list[str]] = [t.value for t in constants.Testament]


def _get_language(_ctx: click.Context, _param: click.Option, value: str) -> models.Language:
    return models.Language(value)


@cli.command("get-chapter")
@click.option("--book", required=True, help="Book name, URL name, or abbreviation (e.g. 'genesis', 'Gen').")
@click.option("--chapter", required=True, type=int, help="Chapter number (1-based).")
@click.option(
    "--language",
    type=click.Choice(_LANGUAGES, case_sensitive=False),
    default=models.Language.ENGLISH,
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
@click.option("--chapter", required=True, type=int, help="Start chapter number (1-based).")
@click.option("--verse", required=True, type=int, help="Start verse number.")
@click.option("--end-chapter", type=int, default=None, help="End chapter for a range (defaults to --chapter).")
@click.option("--end-verse", type=int, default=None, help="End verse for a range (e.g. --end-chapter 2 --end-verse 4).")
@click.option(
    "--language",
    type=click.Choice(_LANGUAGES, case_sensitive=False),
    default="ENGLISH",
    show_default=True,
    callback=_get_language,
    help="Bible language.",
)
async def get_verse(  # noqa: PLR0913
    book: str,
    chapter: int,
    verse: int,
    end_chapter: int | None,
    end_verse: int | None,
    language: models.Language,
) -> None:
    """Fetch a single Bible verse or a range of verses and print to stdout."""
    async with USCCB() as usccb:
        if end_verse is not None:
            end_ch = end_chapter if end_chapter is not None else chapter
            results = await usccb.get_verse_range(book, chapter, verse, end_ch, end_verse, language)
            if not results:
                logger.error(
                    "No verses found: %s %d:%d-%d:%d (%s)", book, chapter, verse, end_ch, end_verse, language.name
                )
                return
            for chapter_num, v in results:
                print(f"{chapter_num}:{v}")  # noqa: T201
        else:
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
@click.option("--save", type=click.Path(dir_okay=False, writable=True), help="Save all chapters to this JSON file.")
@click.option("--include-intro", is_flag=True, default=False, help="Include the book introduction (chapter 0).")
async def get_book(
    book: str,
    language: models.Language,
    save_dir: str | None,
    save: str | None,
    include_intro: bool,  # noqa: FBT001
) -> None:
    """Fetch all chapters of a Bible book and print them to stdout."""
    async with USCCB() as usccb:
        chapters = await usccb.get_book(book, language, include_intro=include_intro)

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

    if save is not None:
        await _io.write_file(Path(save), [chapter.to_dict() for chapter in chapters])


@cli.command("list-books")
@click.argument("testament", required=False, type=click.Choice(_TESTAMENTS, case_sensitive=False), default=None)
async def list_books(testament: str | None) -> None:
    """List Bible books with their chapter counts.

    Optionally filter by TESTAMENT ('old' or 'new'). Omit to list all 73 books.
    """
    t = constants.Testament(testament) if testament is not None else None
    books = t.books if t is not None else constants.ALL_BOOKS

    for book in books:
        print(f"{book.name} ({book.num_chapters} chapters)")  # noqa: T201


async def _fetch_and_write_chapter(
    usccb: USCCB,
    slug: str,
    chapter_num: int,
    language: models.Language,
    path: Path,
) -> bool:
    """Fetch one chapter and write it to *path*. Returns True on success.

    Chapter 0 (intro) returning None is silently ignored.
    """
    try:
        chapter = await usccb.get_chapter(slug, chapter_num, language)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to fetch %s chapter %d", slug, chapter_num)
        return False
    if chapter is None:
        if chapter_num != 0:
            logger.warning("No content for %s chapter %d", slug, chapter_num)
        return False
    try:
        await _io.write_file(path, chapter.to_dict())
    except Exception:  # noqa: BLE001
        logger.warning("Failed to write %s chapter %d to %s", slug, chapter_num, path)
        return False
    return True


async def _download_book_by_chapter(  # noqa: PLR0913
    usccb: USCCB,
    book_info: constants.BibleBookInfo,
    out: Path,
    language: models.Language,
    sem: asyncio.Semaphore,
    skip_existing: bool,  # noqa: FBT001
    include_intro: bool,  # noqa: FBT001
) -> tuple[str, int]:
    """Download all chapters of *book_info* as individual files under out/<slug>/.

    Returns (bucket, chapters_written) where bucket is 'downloaded', 'skipped', or 'failed'.
    """
    slug = utils.book_url_name(book_info)
    book_dir = out / slug
    chapter_nums = list(range(1, book_info.num_chapters + 1))
    if include_intro:
        chapter_nums = [0, *chapter_nums]

    missing = [n for n in chapter_nums if not (book_dir / f"{n:03d}.json").exists()] if skip_existing else chapter_nums

    if not missing:
        return ("skipped", 0)

    async with sem:
        results = await asyncio.gather(
            *[_fetch_and_write_chapter(usccb, slug, n, language, book_dir / f"{n:03d}.json") for n in missing],
            return_exceptions=True,
        )

    written = sum(1 for r in results if r is True)
    if written == 0:
        return ("failed", 0)
    return ("downloaded", written)


async def _download_book_by_book(  # noqa: PLR0913
    usccb: USCCB,
    book_info: constants.BibleBookInfo,
    out: Path,
    language: models.Language,
    sem: asyncio.Semaphore,
    skip_existing: bool,  # noqa: FBT001
    include_intro: bool,  # noqa: FBT001
) -> tuple[str, int]:
    """Download all chapters of *book_info* as a single JSON array file at out/<slug>.json.

    Returns (bucket, chapters_written) where bucket is 'downloaded', 'skipped', or 'failed'.
    """
    slug = utils.book_url_name(book_info)
    book_path = out / f"{slug}.json"

    if skip_existing and book_path.exists():
        return ("skipped", 0)

    async with sem:
        try:
            chapters = await usccb.get_book(slug, language, include_intro=include_intro)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to fetch %s: %s", book_info.name, e)  # noqa: TRY400
            return ("failed", 0)

    if len(chapters) < book_info.num_chapters:
        logger.error(
            "Expected %d chapters for %s, got %d",
            book_info.num_chapters,
            book_info.name,
            len(chapters),
        )
        return ("failed", 0)

    try:
        await _io.write_file(book_path, [c.to_dict() for c in chapters])
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to write %s: %s", book_info.name, e)  # noqa: TRY400
        return ("failed", 0)

    return ("downloaded", book_info.num_chapters)


@cli.command("download-bible")
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, writable=True),
    help="Directory to save downloaded JSON files.",
)
@click.option(
    "--testament",
    type=click.Choice(_TESTAMENTS, case_sensitive=False),
    default=None,
    show_default=True,
    help="Filter to a single testament ('old' or 'new'). Omit for all 73 books.",
)
@click.option(
    "--language",
    type=click.Choice(_LANGUAGES, case_sensitive=False),
    default="ENGLISH",
    show_default=True,
    callback=_get_language,
    help="Bible language.",
)
@click.option(
    "--by-chapter/--by-book",
    default=True,
    show_default=True,
    help="Save each chapter as a separate JSON file, or one file per book.",
)
@click.option(
    "--concurrency",
    type=click.IntRange(min=1),
    default=4,
    show_default=True,
    help="Maximum number of books to download in parallel.",
)
@click.option(
    "--skip-existing/--no-skip-existing",
    default=True,
    show_default=True,
    help="Skip downloading files that already exist on disk.",
)
@click.option(
    "--include-intro/--no-include-intro",
    default=False,
    show_default=True,
    help="Include the book introduction chapter (chapter 0) if available.",
)
async def download_bible(  # noqa: PLR0913
    output_dir: str,
    testament: str | None,
    language: models.Language,
    by_chapter: bool,  # noqa: FBT001
    concurrency: int,
    skip_existing: bool,  # noqa: FBT001
    include_intro: bool,  # noqa: FBT001
) -> None:
    """Download the entire Bible (or a subset) to a directory as JSON files."""
    out = Path(output_dir)
    books = constants.Testament(testament).books if testament is not None else constants.ALL_BOOKS
    sem = asyncio.Semaphore(concurrency)

    async with USCCB() as usccb:
        if by_chapter:
            coros = [
                _download_book_by_chapter(usccb, book_info, out, language, sem, skip_existing, include_intro)
                for book_info in books
            ]
        else:
            coros = [
                _download_book_by_book(usccb, book_info, out, language, sem, skip_existing, include_intro)
                for book_info in books
            ]
        raw_results = await asyncio.gather(*coros, return_exceptions=True)

    downloaded = skipped = failed = total_chapters = 0
    for book_info, result in zip(books, raw_results):
        if isinstance(result, BaseException):
            logger.error("Unexpected error processing %s: %s", book_info.name, result)
            failed += 1
        else:
            bucket, chapters = result
            if bucket == "downloaded":
                downloaded += 1
                total_chapters += chapters
            elif bucket == "skipped":
                skipped += 1
            else:
                failed += 1

    print(  # noqa: T201
        f"Downloaded {downloaded} books ({total_chapters} chapters). {skipped} books skipped. {failed} books failed."
    )
