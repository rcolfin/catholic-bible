# download-bible Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `download-bible` CLI command that downloads the full Catholic Bible (or a filtered subset) to a local directory as JSON files, with concurrency control, skip-existing, and intro-chapter support.

**Architecture:** A single new async command `download_bible` added to `catholic_bible/commands/bible.py`, backed by two private helper coroutines (`_fetch_and_write_chapter`, `_download_book_by_chapter`, `_download_book_by_book`) that return `(bucket, chapters_written)` tuples. The outer command gathers all book coroutines and prints a summary line.

**Tech Stack:** `asyncclick`, `asyncio.Semaphore`, `asyncio.gather`, existing `USCCB` client, `_io.write_file`, `utils.book_url_name`, `constants.ALL_BOOKS` / `Testament`.

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `catholic_bible/commands/bible.py` | Modify | Add `import asyncio`, `from catholic_bible import utils`; add three private helpers and the `download_bible` command |
| `tests/test_commands.py` | Modify | Add all `download-bible` tests |

---

## Task 1: Stub command + smoke test

Add a minimal stub so the command is wired up and discoverable. Write the smoke test first.

**Files:**
- Modify: `tests/test_commands.py`
- Modify: `catholic_bible/commands/bible.py`

- [ ] **Step 1: Write the failing smoke test**

Append to `tests/test_commands.py`:

```python
@pytest.mark.asyncio
async def test_download_bible_requires_output_dir(runner: CliRunner) -> None:
    result = await runner.invoke(cli, ["download-bible"])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
uv run pytest tests/test_commands.py::test_download_bible_requires_output_dir -v
```

Expected: FAIL — `download-bible` command not found.

- [ ] **Step 3: Add stub command to `bible.py`**

Add at the top of `catholic_bible/commands/bible.py`, after the existing imports:

```python
import asyncio
```

Also add `utils` to the existing `catholic_bible` import line:

```python
from catholic_bible import USCCB, _io, constants, models, utils
```

Append the stub to the bottom of `catholic_bible/commands/bible.py`:

```python
@cli.command("download-bible")
@click.option("--output-dir", required=True, type=click.Path(file_okay=False, writable=True), help="Directory to save downloaded JSON files.")
@click.option("--testament", type=click.Choice(_TESTAMENTS, case_sensitive=False), default=None, show_default=True, help="Filter to a single testament ('old' or 'new'). Omit for all 73 books.")
@click.option(
    "--language",
    type=click.Choice(_LANGUAGES, case_sensitive=False),
    default="ENGLISH",
    show_default=True,
    callback=_get_language,
    help="Bible language.",
)
@click.option("--by-chapter/--by-book", default=True, show_default=True, help="Save each chapter as a separate JSON file, or one file per book.")
@click.option("--concurrency", type=click.IntRange(min=1), default=4, show_default=True, help="Maximum number of books to download in parallel.")
@click.option("--skip-existing/--no-skip-existing", default=True, show_default=True, help="Skip downloading files that already exist on disk.")
@click.option("--include-intro/--no-include-intro", default=False, show_default=True, help="Include the book introduction chapter (chapter 0) if available.")
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
```

- [ ] **Step 4: Run smoke test — confirm passes**

```bash
uv run pytest tests/test_commands.py::test_download_bible_requires_output_dir -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite — confirm nothing broken**

```bash
uv run pytest
```

Expected: all existing tests pass (stub command with no body raises `NotImplementedError` or similar — that's fine for now, the smoke test only checks the missing arg case).

- [ ] **Step 6: Commit**

```bash
git add catholic_bible/commands/bible.py tests/test_commands.py
git commit -m "feat: add download-bible command stub"
```

---

## Task 2: `_fetch_and_write_chapter` helper (TDD)

A private coroutine that fetches one chapter and writes it to a given path. Returns `True` on success, `False` on any failure (silently for chapter 0, with a warning otherwise).

**Files:**
- Modify: `tests/test_commands.py`
- Modify: `catholic_bible/commands/bible.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_commands.py`:

```python
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


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
    from catholic_bible.commands.bible import _fetch_and_write_chapter

    chapter = _make_chapter("ruth", 1)
    mock_usccb = AsyncMock()
    mock_usccb.get_chapter = AsyncMock(return_value=chapter)

    dest = tmp_path / "ruth" / "001.json"
    result = await _fetch_and_write_chapter(mock_usccb, "ruth", 1, models.Language.ENGLISH, dest)

    assert result is True
    assert dest.exists()


@pytest.mark.asyncio
async def test_fetch_and_write_chapter_none_non_intro(tmp_path: Path) -> None:
    from catholic_bible.commands.bible import _fetch_and_write_chapter

    mock_usccb = AsyncMock()
    mock_usccb.get_chapter = AsyncMock(return_value=None)

    dest = tmp_path / "ruth" / "001.json"
    result = await _fetch_and_write_chapter(mock_usccb, "ruth", 1, models.Language.ENGLISH, dest)

    assert result is False
    assert not dest.exists()


@pytest.mark.asyncio
async def test_fetch_and_write_chapter_none_intro_silent(tmp_path: Path) -> None:
    """Chapter 0 returning None should be silent (no warning), not counted as error."""
    from catholic_bible.commands.bible import _fetch_and_write_chapter

    mock_usccb = AsyncMock()
    mock_usccb.get_chapter = AsyncMock(return_value=None)

    dest = tmp_path / "ruth" / "000.json"
    result = await _fetch_and_write_chapter(mock_usccb, "ruth", 0, models.Language.ENGLISH, dest)

    assert result is False
    assert not dest.exists()
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
uv run pytest tests/test_commands.py::test_fetch_and_write_chapter_success tests/test_commands.py::test_fetch_and_write_chapter_none_non_intro tests/test_commands.py::test_fetch_and_write_chapter_none_intro_silent -v
```

Expected: ImportError — `_fetch_and_write_chapter` not found.

- [ ] **Step 3: Implement `_fetch_and_write_chapter` in `bible.py`**

Add before the `download_bible` command:

```python
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
    except Exception:
        logger.warning("Failed to fetch %s chapter %d", slug, chapter_num)
        return False
    if chapter is None:
        if chapter_num != 0:
            logger.warning("No content for %s chapter %d", slug, chapter_num)
        return False
    try:
        await _io.write_file(path, chapter.to_dict())
    except Exception:
        logger.warning("Failed to write %s chapter %d to %s", slug, chapter_num, path)
        return False
    return True
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
uv run pytest tests/test_commands.py::test_fetch_and_write_chapter_success tests/test_commands.py::test_fetch_and_write_chapter_none_non_intro tests/test_commands.py::test_fetch_and_write_chapter_none_intro_silent -v
```

Expected: all PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add catholic_bible/commands/bible.py tests/test_commands.py
git commit -m "feat: add _fetch_and_write_chapter helper"
```

---

## Task 3: By-chapter mode end-to-end (TDD)

Implement `_download_book_by_chapter` and wire it into `download_bible`. Test the full CLI round-trip.

**Files:**
- Modify: `tests/test_commands.py`
- Modify: `catholic_bible/commands/bible.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_commands.py`:

```python
@pytest.mark.asyncio
async def test_download_bible_by_chapter(runner: CliRunner, tmp_path: Path) -> None:
    """By-chapter mode writes one file per chapter under <book_slug>/NNN.json."""
    # Ruth has 4 chapters — small enough for a fast test
    chapters = [_make_chapter("ruth", n) for n in range(1, 5)]

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(side_effect=lambda book, ch, lang: next(
            (c for c in chapters if c.number == ch), None
        ))
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    ruth_dir = tmp_path / "ruth"
    assert ruth_dir.is_dir()
    for n in range(1, 5):
        assert (ruth_dir / f"{n:03d}.json").exists(), f"Missing ruth/{n:03d}.json"
    assert "Downloaded" in result.output
```

- [ ] **Step 2: Run it — confirm it fails**

```bash
uv run pytest tests/test_commands.py::test_download_bible_by_chapter -v
```

Expected: FAIL — command body not implemented.

- [ ] **Step 3: Implement `_download_book_by_chapter` and wire into `download_bible`**

Add before the `download_bible` command in `bible.py`:

```python
async def _download_book_by_chapter(
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

    if skip_existing:
        missing = [n for n in chapter_nums if not (book_dir / f"{n:03d}.json").exists()]
    else:
        missing = chapter_nums

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
```

Replace the stub `download_bible` body with the full implementation:

```python
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
        f"Downloaded {downloaded} books ({total_chapters} chapters). "
        f"{skipped} books skipped. {failed} books failed."
    )
```

Note: `_download_book_by_book` is referenced but not yet implemented — add a temporary placeholder so the file is valid:

```python
async def _download_book_by_book(
    usccb: USCCB,
    book_info: constants.BibleBookInfo,
    out: Path,
    language: models.Language,
    sem: asyncio.Semaphore,
    skip_existing: bool,  # noqa: FBT001
    include_intro: bool,  # noqa: FBT001
) -> tuple[str, int]:
    raise NotImplementedError
```

- [ ] **Step 4: Run test — confirm it passes**

```bash
uv run pytest tests/test_commands.py::test_download_bible_by_chapter -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add catholic_bible/commands/bible.py tests/test_commands.py
git commit -m "feat: implement download-bible by-chapter mode"
```

---

## Task 4: By-book mode end-to-end (TDD)

Implement `_download_book_by_book` and test it.

**Files:**
- Modify: `tests/test_commands.py`
- Modify: `catholic_bible/commands/bible.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_commands.py`:

```python
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

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--by-book",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    ruth_file = tmp_path / "ruth.json"
    assert ruth_file.exists()
    import json
    data = json.loads(ruth_file.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 4  # noqa: PLR2004
    assert data[0]["book"] == "ruth"
```

- [ ] **Step 2: Run it — confirm it fails**

```bash
uv run pytest tests/test_commands.py::test_download_bible_by_book -v
```

Expected: FAIL — `_download_book_by_book` raises `NotImplementedError`.

- [ ] **Step 3: Implement `_download_book_by_book`**

Replace the placeholder `_download_book_by_book` stub with the real implementation:

```python
async def _download_book_by_book(
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
        except Exception as e:
            logger.error("Failed to fetch %s: %s", book_info.name, e)
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
    except Exception as e:
        logger.error("Failed to write %s: %s", book_info.name, e)
        return ("failed", 0)

    return ("downloaded", book_info.num_chapters)
```

- [ ] **Step 4: Run test — confirm it passes**

```bash
uv run pytest tests/test_commands.py::test_download_bible_by_book -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add catholic_bible/commands/bible.py tests/test_commands.py
git commit -m "feat: implement download-bible by-book mode"
```

---

## Task 5: Skip-existing logic (TDD)

Test that existing files are skipped and missing ones are fetched.

**Files:**
- Modify: `tests/test_commands.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_commands.py`:

```python
@pytest.mark.asyncio
async def test_download_bible_skip_existing_chapter(runner: CliRunner, tmp_path: Path) -> None:
    """By-chapter: chapters whose file already exists are not re-fetched."""
    # Pre-create chapters 1 and 2 for Ruth (4 chapters total)
    ruth_dir = tmp_path / "ruth"
    ruth_dir.mkdir()
    import json as _json
    for n in (1, 2):
        (ruth_dir / f"{n:03d}.json").write_text(_json.dumps({"pre": "existing"}), encoding="utf-8")

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(return_value=_make_chapter("ruth", 3))
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    # Only Ruth chapters 3 and 4 should be fetched (filter to Ruth to avoid noise from other OT books)
    ruth_calls = [call.args[1] for call in mock_usccb.get_chapter.call_args_list if call.args[0] == "ruth"]
    assert 1 not in ruth_calls
    assert 2 not in ruth_calls
    assert 3 in ruth_calls
    assert 4 in ruth_calls


@pytest.mark.asyncio
async def test_download_bible_skip_existing_book(runner: CliRunner, tmp_path: Path) -> None:
    """By-book: books whose file already exists are not re-fetched."""
    import json as _json
    (tmp_path / "ruth.json").write_text(_json.dumps([]), encoding="utf-8")

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_book = AsyncMock(return_value=[])
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--by-book",
            "--skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    # Ruth's get_book should never be called
    ruth_calls = [
        c for c in mock_usccb.get_book.call_args_list if c.args[0] == "ruth"
    ]
    assert not ruth_calls


@pytest.mark.asyncio
async def test_download_bible_all_chapters_exist_counts_as_skipped(runner: CliRunner, tmp_path: Path) -> None:
    """By-chapter: book with all chapter files present counts as Skipped in summary."""
    import json as _json
    ruth_dir = tmp_path / "ruth"
    ruth_dir.mkdir()
    for n in range(1, 5):  # Ruth has 4 chapters
        (ruth_dir / f"{n:03d}.json").write_text(_json.dumps({}), encoding="utf-8")

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        # Return None for all chapters so other OT books don't cause JSON-serialization errors
        mock_usccb.get_chapter = AsyncMock(return_value=None)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    assert "1 books skipped" in result.output
    # Ruth's chapters were never fetched (all existed)
    ruth_calls = [c for c in mock_usccb.get_chapter.call_args_list if c.args[0] == "ruth"]
    assert not ruth_calls
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
uv run pytest tests/test_commands.py::test_download_bible_skip_existing_chapter tests/test_commands.py::test_download_bible_skip_existing_book tests/test_commands.py::test_download_bible_all_chapters_exist_counts_as_skipped -v
```

Expected: some FAIL (skip logic already partially in place but tests may need tuning).

- [ ] **Step 3: Run the full suite to see current state**

```bash
uv run pytest tests/test_commands.py -v
```

Fix any issues found without changing test intent.

- [ ] **Step 4: Run all three skip tests — confirm they pass**

```bash
uv run pytest tests/test_commands.py::test_download_bible_skip_existing_chapter tests/test_commands.py::test_download_bible_skip_existing_book tests/test_commands.py::test_download_bible_all_chapters_exist_counts_as_skipped -v
```

Expected: all PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_commands.py
git commit -m "test: add skip-existing tests for download-bible"
```

---

## Task 6: Error handling (TDD)

Test that failures are non-fatal and counted correctly.

**Files:**
- Modify: `tests/test_commands.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_commands.py`:

```python
@pytest.mark.asyncio
async def test_download_bible_chapter_none_counts_as_failed(runner: CliRunner, tmp_path: Path) -> None:
    """By-chapter: book where all chapters return None is counted as Failed."""
    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(return_value=None)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    # All 46 OT books failed (every chapter returned None)
    assert "46 books failed" in result.output


@pytest.mark.asyncio
async def test_download_bible_by_book_count_mismatch_is_failed(runner: CliRunner, tmp_path: Path) -> None:
    """By-book: if get_book returns fewer chapters than expected, book is Failed."""
    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        # Ruth has 4 chapters; return only 2
        mock_usccb.get_book = AsyncMock(return_value=[_make_chapter("ruth", n) for n in (1, 2)])
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--by-book",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    assert not (tmp_path / "ruth.json").exists()
    assert "books failed" in result.output


@pytest.mark.asyncio
async def test_download_bible_book_exception_continues(runner: CliRunner, tmp_path: Path) -> None:
    """By-book: exception from get_book is non-fatal, continues to next book."""
    chapters = [_make_chapter("ruth", n) for n in range(1, 5)]

    call_count = 0

    async def get_book_side_effect(book: str, *_args: object, **_kwargs: object) -> list[models.BibleChapter]:
        nonlocal call_count
        call_count += 1
        if book == "ruth":
            raise RuntimeError("network error")
        return chapters

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_book = AsyncMock(side_effect=get_book_side_effect)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--by-book",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    assert not (tmp_path / "ruth.json").exists()
    # All 46 books were attempted
    assert call_count == 46  # noqa: PLR2004


@pytest.mark.asyncio
async def test_download_bible_concurrency_zero_rejected(runner: CliRunner, tmp_path: Path) -> None:
    result = await runner.invoke(cli, [
        "download-bible",
        "--output-dir", str(tmp_path),
        "--concurrency", "0",
    ])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
uv run pytest tests/test_commands.py::test_download_bible_chapter_none_counts_as_failed tests/test_commands.py::test_download_bible_by_book_count_mismatch_is_failed tests/test_commands.py::test_download_bible_book_exception_continues tests/test_commands.py::test_download_bible_concurrency_zero_rejected -v
```

- [ ] **Step 3: Fix any issues**

If tests fail for reasons other than not-yet-implemented logic, adjust the implementation. The error handling is already in `_download_book_by_chapter` and `_download_book_by_book` from the previous tasks — these tests should pass as-is after checking the test assertions align with the actual output format.

- [ ] **Step 4: Run all error tests — confirm pass**

```bash
uv run pytest tests/test_commands.py::test_download_bible_chapter_none_counts_as_failed tests/test_commands.py::test_download_bible_by_book_count_mismatch_is_failed tests/test_commands.py::test_download_bible_book_exception_continues tests/test_commands.py::test_download_bible_concurrency_zero_rejected -v
```

Expected: all PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_commands.py
git commit -m "test: add error-handling tests for download-bible"
```

---

## Task 7: Testament filter, language, and summary (TDD)

Test `--testament`, `--language`, and the summary line format.

**Files:**
- Modify: `tests/test_commands.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_commands.py`:

```python
@pytest.mark.asyncio
async def test_download_bible_testament_old_filter(runner: CliRunner, tmp_path: Path) -> None:
    """--testament old processes only the 46 OT books."""
    fetched_books: list[str] = []

    async def get_chapter_spy(book: str, chapter: int, lang: object) -> models.BibleChapter:
        fetched_books.append(book)
        return _make_chapter(book, chapter)

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(side_effect=get_chapter_spy)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    unique_books = set(fetched_books)
    assert "genesis" in unique_books
    assert "malachi" in unique_books
    assert "matthew" not in unique_books


@pytest.mark.asyncio
async def test_download_bible_testament_new_filter(runner: CliRunner, tmp_path: Path) -> None:
    """--testament new processes only the 27 NT books."""
    fetched_books: list[str] = []

    async def get_chapter_spy(book: str, chapter: int, lang: object) -> models.BibleChapter:
        fetched_books.append(book)
        return _make_chapter(book, chapter)

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(side_effect=get_chapter_spy)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "new",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    unique_books = set(fetched_books)
    assert "matthew" in unique_books
    assert "revelation" in unique_books
    assert "genesis" not in unique_books


@pytest.mark.asyncio
async def test_download_bible_language_passed_through(runner: CliRunner, tmp_path: Path) -> None:
    """--language spanish passes Language.SPANISH to get_chapter."""
    received_langs: list[models.Language] = []

    async def get_chapter_spy(book: str, chapter: int, lang: models.Language) -> models.BibleChapter:
        received_langs.append(lang)
        return _make_chapter(book, chapter)

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(side_effect=get_chapter_spy)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--language", "spanish",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    assert all(lang == models.Language.SPANISH for lang in received_langs)


@pytest.mark.asyncio
async def test_download_bible_summary_line(runner: CliRunner, tmp_path: Path) -> None:
    """Summary line format: 'Downloaded X books (Y chapters). Z books skipped. W books failed.'"""
    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(return_value=_make_chapter("ruth", 1))
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    assert "Downloaded" in result.output
    assert "books skipped" in result.output
    assert "books failed" in result.output
    assert "chapters" in result.output


@pytest.mark.asyncio
async def test_download_bible_exit_code_zero_on_failure(runner: CliRunner, tmp_path: Path) -> None:
    """Command exits 0 even when all books fail."""
    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(return_value=None)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "new",
            "--no-skip-existing",
        ])

    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests — confirm they fail or show expected output**

```bash
uv run pytest tests/test_commands.py::test_download_bible_testament_old_filter tests/test_commands.py::test_download_bible_testament_new_filter tests/test_commands.py::test_download_bible_language_passed_through tests/test_commands.py::test_download_bible_summary_line tests/test_commands.py::test_download_bible_exit_code_zero_on_failure -v
```

- [ ] **Step 3: Fix any issues and confirm all pass**

```bash
uv run pytest tests/test_commands.py::test_download_bible_testament_old_filter tests/test_commands.py::test_download_bible_testament_new_filter tests/test_commands.py::test_download_bible_language_passed_through tests/test_commands.py::test_download_bible_summary_line tests/test_commands.py::test_download_bible_exit_code_zero_on_failure -v
```

- [ ] **Step 4: Run full suite**

```bash
uv run pytest
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_commands.py
git commit -m "test: add testament filter, language, and summary tests for download-bible"
```

---

## Task 8: Intro chapter (TDD)

Test `--include-intro` behaviour in both modes.

**Files:**
- Modify: `tests/test_commands.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_commands.py`:

```python
@pytest.mark.asyncio
async def test_download_bible_include_intro_by_chapter(runner: CliRunner, tmp_path: Path) -> None:
    """--include-intro fetches chapter 0 and writes 000.json when it returns non-None."""
    intro = _make_chapter("ruth", 0)
    chapters = {n: _make_chapter("ruth", n) for n in range(0, 5)}

    async def get_chapter_spy(book: str, chapter: int, lang: object) -> models.BibleChapter | None:
        return chapters.get(chapter)

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(side_effect=get_chapter_spy)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--include-intro",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    ruth_dir = tmp_path / "ruth"
    assert (ruth_dir / "000.json").exists(), "Intro (000.json) should be written"
    assert (ruth_dir / "001.json").exists()


@pytest.mark.asyncio
async def test_download_bible_include_intro_none_is_silent(runner: CliRunner, tmp_path: Path) -> None:
    """--include-intro with chapter 0 returning None produces no warning and no file."""
    chapters = {n: _make_chapter("ruth", n) for n in range(1, 5)}

    async def get_chapter_spy(book: str, chapter: int, lang: object) -> models.BibleChapter | None:
        return chapters.get(chapter)  # chapter 0 returns None

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(side_effect=get_chapter_spy)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--include-intro",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    ruth_dir = tmp_path / "ruth"
    assert not (ruth_dir / "000.json").exists(), "No intro file when chapter 0 returns None"
    assert (ruth_dir / "001.json").exists()


@pytest.mark.asyncio
async def test_download_bible_no_include_intro_default(runner: CliRunner, tmp_path: Path) -> None:
    """Chapter 0 is never fetched when --no-include-intro (default)."""
    fetched_chapters: list[int] = []

    async def get_chapter_spy(book: str, chapter: int, lang: object) -> models.BibleChapter:
        fetched_chapters.append(chapter)
        return _make_chapter(book, chapter)

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_chapter = AsyncMock(side_effect=get_chapter_spy)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    assert 0 not in fetched_chapters


@pytest.mark.asyncio
async def test_download_bible_include_intro_by_book(runner: CliRunner, tmp_path: Path) -> None:
    """--include-intro passes include_intro=True to get_book in by-book mode."""
    chapters = [_make_chapter("ruth", n) for n in range(0, 5)]  # 5 items: intro + 4 chapters

    with patch("catholic_bible.commands.bible.USCCB") as mock_cls:
        mock_usccb = AsyncMock()
        mock_usccb.__aenter__ = AsyncMock(return_value=mock_usccb)
        mock_usccb.__aexit__ = AsyncMock(return_value=None)
        mock_usccb.get_book = AsyncMock(return_value=chapters)
        mock_cls.return_value = mock_usccb

        result = await runner.invoke(cli, [
            "download-bible",
            "--output-dir", str(tmp_path),
            "--testament", "old",
            "--by-book",
            "--include-intro",
            "--no-skip-existing",
            "--concurrency", "1",
        ])

    assert result.exit_code == 0
    ruth_file = tmp_path / "ruth.json"
    assert ruth_file.exists()
    # Confirm include_intro=True was passed to get_book
    call_kwargs = mock_usccb.get_book.call_args_list[0]
    assert call_kwargs.kwargs.get("include_intro") is True or (len(call_kwargs.args) > 2 and call_kwargs.args[2] is True)
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
uv run pytest tests/test_commands.py::test_download_bible_include_intro_by_chapter tests/test_commands.py::test_download_bible_include_intro_none_is_silent tests/test_commands.py::test_download_bible_no_include_intro_default tests/test_commands.py::test_download_bible_include_intro_by_book -v
```

- [ ] **Step 3: Fix any issues and confirm all pass**

```bash
uv run pytest tests/test_commands.py::test_download_bible_include_intro_by_chapter tests/test_commands.py::test_download_bible_include_intro_none_is_silent tests/test_commands.py::test_download_bible_no_include_intro_default tests/test_commands.py::test_download_bible_include_intro_by_book -v
```

Expected: all PASS.

- [ ] **Step 4: Run full suite**

```bash
uv run pytest
```

Expected: all tests pass (including mypy, ruff, doctest).

- [ ] **Step 5: Commit**

```bash
git add tests/test_commands.py
git commit -m "test: add include-intro tests for download-bible"
```

---

## Task 9: Final check and cleanup

- [ ] **Step 1: Run full test suite one final time**

```bash
uv run pytest
```

Expected: green across all checks (pytest, mypy, ruff, ruff-format, doctests).

- [ ] **Step 2: Smoke-test the CLI manually**

```bash
uv run python -m catholic_bible download-bible --help
```

Verify all options are listed with their defaults and help text.

- [ ] **Step 3: Commit if any cleanup was needed**

```bash
git add -p
git commit -m "chore: final cleanup for download-bible command"
```
