# download-bible CLI Command — Design Spec

**Date:** 2026-03-25
**Status:** Approved

## Overview

Add a `download-bible` CLI command to `catholic_bible/commands/bible.py`. Reuses `USCCB`, `_io.write_file`, `utils.book_url_name`. No new files needed.

## CLI Interface

```
uv run python -m catholic_bible download-bible --output-dir ./bible-data [OPTIONS]
```

All options include `show_default=True` and a `help=` string.

| Option | Click declaration | Default | Help text |
|--------|-------------------|---------|-----------|
| `--output-dir` | `click.Path(file_okay=False, writable=True)` → `str`, required | — | `"Directory to save downloaded JSON files."` |
| `--testament` | `click.Choice(_TESTAMENTS, case_sensitive=False)` → `str \| None` | `None` (all books) | `"Filter to a single testament ('old' or 'new'). Omit for all 73 books."` |
| `--language` | `click.Choice(_LANGUAGES, case_sensitive=False)`, `callback=_get_language` → `models.Language` | `"ENGLISH"` | `"Bible language."` |
| `--by-chapter/--by-book` | single option → `by_chapter: bool` | `True` (`--by-chapter`) | `"Save each chapter as a separate JSON file, or one file per book."` |
| `--concurrency` | `type=click.IntRange(min=1)` → `int` | `4` | `"Maximum number of books to download in parallel."` |
| `--skip-existing/--no-skip-existing` | single option → `skip_existing: bool` | `True` | `"Skip downloading files that already exist on disk."` |
| `--include-intro/--no-include-intro` | single option → `include_intro: bool` | `False` | `"Include the book introduction chapter (chapter 0) if available."` |

**Click declarations:**
```python
@cli.command("download-bible")
@click.option("--output-dir", required=True, type=click.Path(file_okay=False, writable=True), help="...")
@click.option("--testament", type=click.Choice(_TESTAMENTS, case_sensitive=False), default=None, show_default=True, help="...")
@click.option("--language", type=click.Choice(_LANGUAGES, case_sensitive=False), default="ENGLISH", show_default=True, callback=_get_language, help="...")
@click.option("--by-chapter/--by-book", default=True, show_default=True, help="...")
@click.option("--concurrency", type=click.IntRange(min=1), default=4, show_default=True, help="...")
@click.option("--skip-existing/--no-skip-existing", default=True, show_default=True, help="...")
@click.option("--include-intro/--no-include-intro", default=False, show_default=True, help="...")
async def download_bible(  # noqa: PLR0913
    output_dir: str,
    testament: str | None,
    language: models.Language,
    by_chapter: bool,  # noqa: FBT001
    concurrency: int,
    skip_existing: bool,  # noqa: FBT001
    include_intro: bool,  # noqa: FBT001
) -> None:
```

`output_dir` arrives as `str` (Click `Path` without `path_type`) — wrap manually: `out = Path(output_dir)`. Follow the existing `get-book` convention.

## File Layout

All directory and file names use `utils.book_url_name(book_info)` (URL slug, e.g. `'genesis'`, `'1corinthians'`).

### By-chapter mode (default)

```
<output-dir>/
  genesis/
    001.json
    002.json
    ...
  exodus/
    001.json
    ...
```

Each file: `BibleChapter.to_dict()` (a `dict`). Filename: `f"{chapter.number:03d}.json"`.

### By-book mode

```
<output-dir>/
  genesis.json
  exodus.json
  ...
```

Each file: `[c.to_dict() for c in chapters]` (a `list[dict]`). `_io.write_file` accepts both `dict` and `list[dict]`.

## Chapter Enumeration

`BibleBookInfo.num_chapters` is known statically — no network fetch required to enumerate chapters.

- **By-chapter:** iterate `range(1, book_info.num_chapters + 1)` to get chapter numbers. If `include_intro` is `True`, also fetch chapter `0` (the intro) — check if it exists by attempting `get_chapter(slug, 0, language)` and writing it only if the result is not `None`. Call `USCCB.get_chapter(slug, n, language)` for each non-skipped chapter.
- **By-book:** call `USCCB.get_book(slug, language, include_intro=include_intro)`.

`slug = utils.book_url_name(book_info)`. Passing slugs to `get_book`/`get_chapter` is safe — `lookup_book` resolves slugs.

**Intro chapter (chapter 0):** not all books have an intro. `get_chapter(slug, 0, language)` returns `None` if there is no intro for that book — treat exactly like any other `None` result (log nothing; silence is correct since the absence is expected). The intro chapter file, if it exists, is written as `000.json`. The intro is **not** counted in `book_info.num_chapters`, so by-book count validation (`len(chapters) != book_info.num_chapters`) is performed against the non-intro chapters only — `get_book` with `include_intro=True` may return `num_chapters + 1` items; validate `len(chapters) >= book_info.num_chapters` instead.

## Skip Logic

"Skip" means skip the network fetch entirely. The skip check happens **before acquiring the semaphore** so that fully-skipped books do not hold a concurrency slot.

- **By-chapter:** before acquiring the semaphore, check if all chapter files exist (including `000.json` if `include_intro` is `True`). If all exist, mark the book as Skipped and return without acquiring. If some are missing, acquire the semaphore and fetch only the missing chapters.
- **By-book:** before acquiring the semaphore, check if `<output-dir>/<slug>.json` exists. If it exists and `skip_existing`, mark the book as Skipped and return without acquiring.

## Concurrency & Flow

1. Build book list: `constants.Testament(testament).books` if `testament` is not `None`, else `constants.ALL_BOOKS`.
2. Wrap the entire command in `async with USCCB() as usccb:` — one shared instance for all tasks.
3. `sem = asyncio.Semaphore(concurrency)`.
4. For each book, define a coroutine that:
   - Performs the pre-semaphore skip check (see above).
   - Acquires the semaphore (`async with sem:`).
   - Fetches all non-skipped chapters/book inside the semaphore.
   - Returns a result (Downloaded, Skipped, or Failed) to the outer gather.
5. `results = await asyncio.gather(*[book_coro(b) for b in books], return_exceptions=True)` — all coroutines run concurrently, gated by the semaphore.
6. Inspect `results`: any `BaseException` instances indicate programming errors (not expected — all coroutines must swallow their own exceptions internally and return a structured result). Log any unexpected exceptions and treat them as failures.
7. Print summary.

**Semaphore semantics:** the semaphore caps the number of books being actively fetched in parallel. Within a book, all non-skipped chapters are fetched concurrently without an additional throttle — consistent with the existing `get_book` behaviour. With `--concurrency 4` and Psalms (150 chapters), up to 4 books × N chapters = potentially hundreds of simultaneous HTTP requests. This is intentional.

**By-chapter book coroutine (pseudocode):**
```python
async def _download_book_by_chapter(book_info, ...):
    slug = book_url_name(book_info)
    chapter_nums = range(1, book_info.num_chapters + 1)
    missing = [n for n in chapter_nums if not skip_existing or not chapter_path(n).exists()]

    if not missing:
        return Skipped(book_info)

    async with sem:
        chapter_results = await asyncio.gather(
            *[_fetch_chapter(usccb, slug, n, language, out / slug / f"{n:03d}.json") for n in missing],
            return_exceptions=True,
        )
    # _fetch_chapter writes to the path it receives and returns True on success, False/exception otherwise.
    # The output path uses n (the requested chapter number), NOT chapter.number from the returned BibleChapter,
    # so the filename is always predictable from the enumeration range.
    written = sum(1 for r in chapter_results if r is True)  # True on success
    if written == 0:
        return Failed(book_info)
    return Downloaded(book_info, chapters_written=written)
```

**By-book book coroutine (pseudocode):**
```python
async def _download_book_by_book(book_info, ...):
    slug = book_url_name(book_info)
    book_path = out / f"{slug}.json"

    if skip_existing and book_path.exists():
        return Skipped(book_info)

    async with sem:
        try:
            chapters = await usccb.get_book(slug, language)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", book_info.name, e)
            return Failed(book_info)

    if len(chapters) != book_info.num_chapters:
        logger.error("Expected %d chapters for %s, got %d", book_info.num_chapters, book_info.name, len(chapters))
        return Failed(book_info)

    await _io.write_file(book_path, [c.to_dict() for c in chapters])
    return Downloaded(book_info, chapters_written=book_info.num_chapters)
```

## Error Handling

All failures are non-fatal. All exceptions must be caught inside the book coroutine — the outer gather must never receive an exception result in normal operation.

- **By-chapter — `get_chapter` returns `None`:** log warning (include book name + chapter number), do not write file.
- **By-chapter — `get_chapter` raises:** caught by inner gather (`return_exceptions=True`), treated as `None`.
- **By-chapter — `_io.write_file` raises:** log warning, count chapter as not written.
- **By-book — `get_book` raises (incl. `ValueError`):** log error (include book name), return `Failed`.
- **By-book — count mismatch or empty list:** log error (expected N got M), return `Failed`, no file written.
- **By-book — `_io.write_file` raises:** log error, return `Failed`.

**Exit code:** always 0, regardless of failures — consistent with all other commands in `bible.py`. Failures are reported via `logger.error` and the summary line.

## Book Bucket Rules (exactly one bucket per book)

| Condition | Bucket |
|-----------|--------|
| ≥1 chapter file written (by-chapter) | Downloaded |
| Whole-book file written (by-book) | Downloaded |
| All chapters individually skipped / whole-book file skipped | Skipped |
| No files written and ≥1 fetch attempted | Failed |

A partially-written book (some chapters OK, some failed) counts as **Downloaded**. Its chapter contribution to Y is the number of files actually written, not `num_chapters`.

## Summary Output

```
Downloaded X books (Y chapters). Z books skipped. W books failed.
```

- **Y:** by-chapter = total chapter files written across all Downloaded books; by-book = `sum(book_info.num_chapters for written_books)` (static count, not list length).
- **Z:** books in the Skipped bucket.
- **W:** books in the Failed bucket.

## Testing

Tests in `tests/test_commands_bible.py` using asyncclick's `CliRunner` and mocking `USCCB.get_chapter`, `USCCB.get_book`, `Path.exists`, and `_io.write_file`:

- By-chapter: correct file paths `<book_slug>/<NNN>.json` for each chapter.
- By-book: `<book_slug>.json` with list payload containing `to_dict()` output.
- `--skip-existing`: all chapter files exist → `get_chapter` not called, book counted as Skipped.
- `--skip-existing`: some chapter files exist → only missing chapters fetched.
- `--skip-existing`: book file exists → `get_book` not called, book counted as Skipped.
- `--no-skip-existing`: re-fetches even when files exist.
- By-book count mismatch (`len(chapters) < num_chapters`): no file written, book counted as Failed.
- By-chapter all chapters `None`: no files written, book counted as Failed.
- `get_book` raises exception: book counted as Failed, continues to next book.
- `--testament old` / `--testament new`: only the correct 46 / 27 books processed.
- `--language spanish`: `models.Language.SPANISH` passed to `get_book` / `get_chapter`.
- `--concurrency 1`: semaphore allows one book at a time.
- `--concurrency 0`: `result.exit_code != 0` (Click `UsageError`).
- Mixed scenario (some Downloaded, Skipped, Failed): summary counts correct.
- Exit code is always 0 even when some books fail.
- `--include-intro`: intro chapter fetched as `000.json` when `get_chapter(..., 0, ...)` returns non-`None`.
- `--include-intro`: intro silently skipped (no warning) when `get_chapter(..., 0, ...)` returns `None`.
- `--no-include-intro` (default): chapter 0 never fetched.
- `--include-intro` by-book: `get_book(..., include_intro=True)` called; extra intro chapter in result does not trigger count mismatch failure.
