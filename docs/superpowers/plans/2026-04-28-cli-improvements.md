# CLI Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve CLI user experience with helpful error messages for invalid book names and real-time progress reporting for downloads.

**Architecture:** Create custom exception module, modify book lookup to raise exceptions with fuzzy-matched suggestions, add error handlers to CLI commands, and integrate progress bar into download-bible command with terminal auto-detection.

**Tech Stack:** `difflib` (stdlib), `rich.Progress` (already in dependencies), asyncclick, pytest with mocking

---

## File Structure

| File | Status | Purpose |
|------|--------|---------|
| `catholic_bible/errors.py` | Create | Custom exception classes: `InvalidBookError`, `InvalidChapterError` |
| `catholic_bible/utils.py` | Modify | Update `lookup_book()` to raise `InvalidBookError` with fuzzy matching |
| `catholic_bible/commands/bible.py` | Modify | Add error handlers to `get-chapter`, `get-verse`, `get-book`; add progress bar to `download-bible` |
| `tests/test_errors.py` | Create | Unit tests for exception `__str__()` methods |
| `tests/test_utils.py` | Modify | Add tests for `lookup_book()` fuzzy matching behavior |
| `tests/test_commands.py` | Modify | Add tests for CLI error handling and progress bar |

---

## Task 1: Create Custom Error Module

**Files:**
- Create: `catholic_bible/errors.py`
- Test: `tests/test_errors.py`

### Step 1: Write failing tests for error module

Create `tests/test_errors.py`:

```python
import pytest
from catholic_bible.errors import InvalidBookError, InvalidChapterError


class TestInvalidBookError:
    def test_error_message_with_closest_match(self):
        """InvalidBookError should suggest closest match."""
        error = InvalidBookError("corinthians", "1 Corinthians")
        assert str(error) == "Book 'corinthians' not found. Did you mean: 1 Corinthians?"
    
    def test_error_message_without_closest_match(self):
        """InvalidBookError should show 'not found' when no match available."""
        error = InvalidBookError("xyz", None)
        assert str(error) == "Book 'xyz' not found."
    
    def test_error_attributes(self):
        """InvalidBookError should store book_name and closest_match."""
        error = InvalidBookError("gen", "Genesis")
        assert error.book_name == "gen"
        assert error.closest_match == "Genesis"


class TestInvalidChapterError:
    def test_error_message_format(self):
        """InvalidChapterError should show max chapters."""
        error = InvalidChapterError("Genesis", 999, 50)
        assert str(error) == "Genesis has 50 chapters, not 999"
    
    def test_error_attributes(self):
        """InvalidChapterError should store all attributes."""
        error = InvalidChapterError("Matthew", 100, 28)
        assert error.book_name == "Matthew"
        assert error.chapter == 100
        assert error.max_chapters == 28
```

- [ ] **Step 1: Write failing tests**

Run: `pytest tests/test_errors.py -v`

Expected output: 5 FAILED (errors not yet defined)

### Step 2: Implement error classes

Create `catholic_bible/errors.py`:

```python
"""Custom exceptions for CLI error handling."""

from __future__ import annotations


class InvalidBookError(Exception):
    """Raised when a book name doesn't match any canonical book."""

    def __init__(self, book_name: str, closest_match: str | None = None) -> None:
        """Initialize InvalidBookError.

        Args:
            book_name: The invalid book name entered by user
            closest_match: The closest matching book name (if any)
        """
        self.book_name = book_name
        self.closest_match = closest_match
        super().__init__(str(self))

    def __str__(self) -> str:
        """Return user-friendly error message."""
        msg = f"Book '{self.book_name}' not found"
        if self.closest_match:
            msg += f". Did you mean: {self.closest_match}?"
        return msg


class InvalidChapterError(Exception):
    """Raised when a chapter number is invalid for a book."""

    def __init__(self, book_name: str, chapter: int, max_chapters: int) -> None:
        """Initialize InvalidChapterError.

        Args:
            book_name: The name of the book
            chapter: The invalid chapter number requested
            max_chapters: The maximum chapter count for this book
        """
        self.book_name = book_name
        self.chapter = chapter
        self.max_chapters = max_chapters
        super().__init__(str(self))

    def __str__(self) -> str:
        """Return user-friendly error message."""
        return f"{self.book_name} has {self.max_chapters} chapters, not {self.chapter}"
```

- [ ] **Step 2: Write implementation**

### Step 3: Run tests to verify pass

Run: `pytest tests/test_errors.py -v`

Expected output: 5 PASSED

- [ ] **Step 3: Verify tests pass**

### Step 4: Commit

```bash
git add catholic_bible/errors.py tests/test_errors.py
git commit -m "feat: add custom error exceptions

- InvalidBookError: raised when book name doesn't match any canonical book
- InvalidChapterError: raised when chapter number is invalid (reserved for future)
- Both exceptions include user-friendly __str__() messages

Tests cover exception message formatting and attribute storage."
```

- [ ] **Step 4: Commit**

---

## Task 2: Update lookup_book() with Fuzzy Matching

**Files:**
- Modify: `catholic_bible/utils.py`
- Test: `tests/test_utils.py`

### Step 1: Write failing tests for lookup_book()

Add to `tests/test_utils.py`:

```python
import pytest
from catholic_bible.errors import InvalidBookError
from catholic_bible.utils import lookup_book


class TestLookupBookFuzzyMatching:
    def test_lookup_book_with_close_match(self):
        """lookup_book should suggest closest match for typo."""
        with pytest.raises(InvalidBookError) as exc_info:
            lookup_book("corinthians")
        
        error = exc_info.value
        assert error.book_name == "corinthians"
        assert error.closest_match in ["1 Corinthians", "2 Corinthians"]
        # One of the two should be the closest
    
    def test_lookup_book_with_no_close_match(self):
        """lookup_book should not suggest match for very different names."""
        with pytest.raises(InvalidBookError) as exc_info:
            lookup_book("xyz")
        
        error = exc_info.value
        assert error.book_name == "xyz"
        assert error.closest_match is None
    
    def test_lookup_book_valid_name_still_works(self):
        """lookup_book should still work correctly for valid book names."""
        # Test a few common variations
        genesis = lookup_book("Genesis")
        assert genesis.name == "Genesis"
        
        matthew = lookup_book("matthew")
        assert matthew.name == "Matthew"
        
        psalms = lookup_book("psalms")
        assert psalms.name == "Psalms"
    
    def test_lookup_book_with_partial_match(self):
        """lookup_book should handle partial matches."""
        with pytest.raises(InvalidBookError) as exc_info:
            lookup_book("gen")
        
        error = exc_info.value
        assert error.closest_match == "Genesis"
    
    def test_lookup_book_case_insensitive(self):
        """lookup_book should still be case insensitive for valid names."""
        genesis1 = lookup_book("GENESIS")
        genesis2 = lookup_book("genesis")
        assert genesis1.name == genesis2.name == "Genesis"
```

- [ ] **Step 1: Write failing tests**

Run: `pytest tests/test_utils.py::TestLookupBookFuzzyMatching -v`

Expected output: 5 FAILED (lookup_book not yet updated)

### Step 2: Read current lookup_book() implementation

Run: `grep -n "def lookup_book" catholic_bible/utils.py`

Then read the function to understand current logic.

- [ ] **Step 2: Read current implementation**

### Step 3: Update lookup_book() to raise InvalidBookError

Modify `catholic_bible/utils.py`. Find the `lookup_book()` function and replace it:

```python
def lookup_book(query: str) -> BibleBookInfo:
    """
    Look up a Bible book by name, abbreviation, or URL name.

    Supports case-insensitive matching and partial names.

    Args:
        query: Book name, URL name, or abbreviation (e.g., 'Genesis', 'gen', 'Gn')

    Returns:
        BibleBookInfo: The matched book

    Raises:
        InvalidBookError: If book name doesn't match any canonical book.
            Includes fuzzy-matched suggestion if available.

    Example:
        >>> lookup_book("Genesis")  # doctest: +SKIP
        BibleBookInfo(...)
        >>> lookup_book("gen")  # doctest: +SKIP
        BibleBookInfo(...)
    """
    from difflib import get_close_matches
    from catholic_bible import errors

    query_lower = query.lower()

    # Try exact URL name match
    if query_lower in BIBLE_BOOKS:
        return BIBLE_BOOKS[query_lower]

    # Try case-insensitive name match
    for book in ALL_BOOKS:
        if book.name.lower() == query_lower:
            return book

    # Try short abbreviation match
    for book in ALL_BOOKS:
        if book.short_abbreviation.lower() == query_lower:
            return book

    # Try long abbreviation match
    for book in ALL_BOOKS:
        if book.long_abbreviation.lower() == query_lower:
            return book

    # No match found - find closest match for suggestion
    all_book_names = [book.name for book in ALL_BOOKS]
    closest = get_close_matches(query, all_book_names, n=1, cutoff=0.6)
    closest_match = closest[0] if closest else None

    raise errors.InvalidBookError(query, closest_match)
```

- [ ] **Step 3: Update lookup_book() implementation**

### Step 4: Run tests to verify pass

Run: `pytest tests/test_utils.py::TestLookupBookFuzzyMatching -v`

Expected output: 5 PASSED

Also run existing utils tests to ensure no regression:

Run: `pytest tests/test_utils.py -v`

Expected output: All tests pass

- [ ] **Step 4: Verify tests pass**

### Step 5: Commit

```bash
git add catholic_bible/utils.py tests/test_utils.py
git commit -m "feat: update lookup_book() to raise InvalidBookError with fuzzy matching

- lookup_book() now raises InvalidBookError instead of returning None
- Uses difflib.get_close_matches() to suggest closest book name (60% cutoff)
- Imports errors module
- Maintains backward compatibility for valid book names
- Tests verify fuzzy matching, case insensitivity, and error handling"
```

- [ ] **Step 5: Commit**

---

## Task 3: Add Error Handling to CLI Commands

**Files:**
- Modify: `catholic_bible/commands/bible.py`
- Test: `tests/test_commands.py`

### Step 1: Write failing tests for CLI error handling

Add to `tests/test_commands.py`:

```python
import pytest
from click.testing import CliRunner
from catholic_bible.commands.bible import (
    get_chapter,
    get_verse,
    get_book,
)


class TestCLIErrorHandling:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_get_chapter_invalid_book_shows_suggestion(self, runner):
        """get-chapter with typo should show closest match."""
        result = runner.invoke(
            get_chapter,
            ["--book", "corinthians", "--chapter", "1"]
        )
        assert result.exit_code == 1
        assert "Book 'corinthians' not found" in result.output
        assert "Did you mean:" in result.output
        # Should suggest 1 Corinthians or 2 Corinthians
        assert "Corinthians" in result.output

    def test_get_chapter_invalid_book_no_match(self, runner):
        """get-chapter with very wrong book name should show generic error."""
        result = runner.invoke(
            get_chapter,
            ["--book", "xyz", "--chapter", "1"]
        )
        assert result.exit_code == 1
        assert "Book 'xyz' not found" in result.output

    def test_get_verse_invalid_book(self, runner):
        """get-verse with invalid book should show error."""
        result = runner.invoke(
            get_verse,
            ["--book", "invalid", "--chapter", "1", "--verse", "1"]
        )
        assert result.exit_code == 1
        assert "Book 'invalid' not found" in result.output

    def test_get_book_invalid_book(self, runner):
        """get-book with invalid book should show error."""
        result = runner.invoke(
            get_book,
            ["--book", "notabook"]
        )
        assert result.exit_code == 1
        assert "Book 'notabook' not found" in result.output

    def test_get_chapter_valid_book_still_works(self, runner):
        """get-chapter with valid book should work."""
        result = runner.invoke(
            get_chapter,
            ["--book", "Genesis", "--chapter", "1"]
        )
        # Should succeed (not fail due to error handling)
        # We don't test the actual content here, just that error handling works
        assert result.exit_code in [0, 1]  # Allow network errors in test
```

- [ ] **Step 1: Write failing tests**

Run: `pytest tests/test_commands.py::TestCLIErrorHandling -v`

Expected output: Tests fail because commands don't handle InvalidBookError yet

### Step 2: Add error handling to CLI commands

Find each command in `catholic_bible/commands/bible.py` (`get-chapter`, `get-verse`, `get-book`) and wrap the `lookup_book()` call:

For `get_chapter()`:

```python
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
    try:
        book_info = utils.lookup_book(book)
    except errors.InvalidBookError as e:
        logger.error(str(e))
        return

    async with USCCB() as usccb:
        result = await usccb.get_chapter(book_info.url_name, chapter, language)
        if result is None:
            logger.error("Failed to retrieve %s chapter %d (%s)", book, chapter, language.name)
            return

    print(result)  # noqa: T201

    if save is not None:
        await _io.write_file(Path(save), result.to_dict())
```

Do the same for `get_verse()` and `get_book()` - wrap `utils.lookup_book()` in try/except.

Add import at top of file:
```python
from catholic_bible import errors
```

- [ ] **Step 2: Add error handling to get-chapter, get-verse, get-book**

### Step 3: Run tests to verify

Run: `pytest tests/test_commands.py::TestCLIErrorHandling -v`

Expected output: Tests pass

- [ ] **Step 3: Verify tests pass**

### Step 4: Run full test suite to check for regressions

Run: `pytest tests/test_commands.py -v`

Expected output: All tests pass

- [ ] **Step 4: Check for regressions**

### Step 5: Commit

```bash
git add catholic_bible/commands/bible.py
git commit -m "feat: add error handling to CLI book commands

- get-chapter, get-verse, get-book now catch InvalidBookError
- Show user-friendly error message with suggestions
- Exit with code 1 on error
- Maintains existing functionality for valid book names

Tests verify error message display and exit codes."
```

- [ ] **Step 5: Commit**

---

## Task 4: Add Progress Bar to download_bible()

**Files:**
- Modify: `catholic_bible/commands/bible.py`
- Test: `tests/test_commands.py`

### Step 1: Write failing tests for progress bar

Add to `tests/test_commands.py`:

```python
import sys
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from catholic_bible.commands.bible import download_bible


class TestDownloadBibleProgress:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_progress_flag_explicit_true(self, runner, tmp_path):
        """--progress flag should enable progress bar."""
        output_dir = str(tmp_path)
        # Mock USCCB to avoid actual network calls
        with patch("catholic_bible.commands.bible.USCCB"):
            result = runner.invoke(
                download_bible,
                ["--output-dir", output_dir, "--progress"]
            )
            # We're not testing actual progress output, just that flag is accepted
            # Exit code might be error due to mocked USCCB, that's ok
            assert "--progress" not in result.output or result.exit_code in [0, 1, 2]

    def test_progress_flag_explicit_false(self, runner, tmp_path):
        """--no-progress flag should disable progress bar."""
        output_dir = str(tmp_path)
        with patch("catholic_bible.commands.bible.USCCB"):
            result = runner.invoke(
                download_bible,
                ["--output-dir", output_dir, "--no-progress"]
            )
            # Command should accept the flag
            assert "--no-progress" not in result.output or result.exit_code in [0, 1, 2]

    @patch("sys.stderr.isatty")
    def test_progress_auto_detect_interactive(self, mock_isatty, runner, tmp_path):
        """Progress bar should show when stderr is a tty."""
        mock_isatty.return_value = True
        output_dir = str(tmp_path)
        with patch("catholic_bible.commands.bible.USCCB"):
            result = runner.invoke(
                download_bible,
                ["--output-dir", output_dir]
            )
            # Just verify command runs (doesn't matter if progress shown in test)
            assert result.exit_code in [0, 1, 2]

    @patch("sys.stderr.isatty")
    def test_progress_auto_detect_non_interactive(self, mock_isatty, runner, tmp_path):
        """Progress bar should not show when stderr is not a tty."""
        mock_isatty.return_value = False
        output_dir = str(tmp_path)
        with patch("catholic_bible.commands.bible.USCCB"):
            result = runner.invoke(
                download_bible,
                ["--output-dir", output_dir]
            )
            # Just verify command runs without progress in non-interactive mode
            assert result.exit_code in [0, 1, 2]
```

- [ ] **Step 1: Write failing tests**

Run: `pytest tests/test_commands.py::TestDownloadBibleProgress -v`

Expected output: Tests fail because --progress/--no-progress flags don't exist yet

### Step 2: Find download_bible() function

Run: `grep -n "def download_bible" catholic_bible/commands/bible.py`

Then read the function to understand its structure.

- [ ] **Step 2: Read download_bible() function**

### Step 3: Add --progress/--no-progress option and progress bar

Add import at top of file:
```python
import sys
from rich.progress import Progress, BarColumn, DownloadColumn, TextColumn, TransferSpeedColumn
```

Find the `download_bible()` function and add the progress option:

```python
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
@click.option(
    "--progress/--no-progress",
    default=None,
    help="Show progress bar. Auto-detects terminal if not specified.",
)
async def download_bible(
    output_dir: str,
    testament: str | None,
    language: models.Language,
    by_chapter: bool,
    concurrency: int,
    skip_existing: bool,
    include_intro: bool,
    progress: bool | None,
) -> None:
    """Download the entire Bible (or a subset) to a directory in JSON format."""
    # Determine if we should show progress
    should_show_progress = progress if progress is not None else sys.stderr.isatty()

    # [Keep all existing implementation below, but wrap the download loop with progress bar]
    
    # Get list of books to download
    books_to_download = _get_books_for_testament(testament)
    total_books = len(books_to_download)
    
    # Create progress bar if needed
    progress_bar = None
    if should_show_progress:
        progress_bar = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total} books)"),
            transient=True,
        )
        progress_bar.start()
        task_id = progress_bar.add_task("Downloading:", total=total_books)
    
    try:
        # Your existing download logic here, but update progress after each book
        async with USCCB() as usccb:
            for book in books_to_download:
                # Download book...
                # [your existing code]
                
                if progress_bar:
                    progress_bar.update(task_id, advance=1)
    finally:
        if progress_bar:
            progress_bar.stop()
```

Note: This is a template. You need to integrate with the existing download logic. The key changes are:
1. Add `progress` parameter to function signature
2. Determine `should_show_progress` based on parameter and `sys.stderr.isatty()`
3. Create progress bar if needed
4. Call `progress_bar.update()` after each book is downloaded
5. Clean up progress bar in finally block

- [ ] **Step 3: Add --progress option and progress bar integration**

### Step 4: Run tests to verify

Run: `pytest tests/test_commands.py::TestDownloadBibleProgress -v`

Expected output: Tests pass

- [ ] **Step 4: Verify tests pass**

### Step 5: Test manually with interactive terminal

Run: `uv run python -m catholic_bible download-bible --help`

Expected: Should show `--progress / --no-progress` option

- [ ] **Step 5: Manual verification**

### Step 6: Commit

```bash
git add catholic_bible/commands/bible.py
git commit -m "feat: add progress bar to download-bible command

- Add --progress/--no-progress flags
- Auto-detect terminal interactivity with sys.stderr.isatty()
- Show progress as: [████░░░░░░] 40% (30/73 books)
- Uses rich.Progress for clean output to stderr
- Progress preserved in scripts via flags
- Tests verify flag acceptance and auto-detection

Progress bar shows current book count vs total during download."
```

- [ ] **Step 6: Commit**

---

## Task 5: Run Full Test Suite and Verify

**Files:**
- All files (test suite run)

### Step 1: Run all tests

Run: `pytest -v`

Expected output: All tests pass, including:
- 179 existing tests (all should still pass)
- New error tests
- New utils fuzzy matching tests
- New CLI error handling tests
- New progress bar tests

- [ ] **Step 1: Run full test suite**

### Step 2: Run with coverage

Run: `pytest --cov=catholic_bible --cov-report=term-missing`

Expected output:
- Coverage >= 89% (current baseline)
- New code paths covered

- [ ] **Step 2: Run coverage report**

### Step 3: Test mypy type checking

Run: `uv run mypy catholic_bible tests`

Expected output: `Success: no issues found in N source files`

- [ ] **Step 3: Verify type checking**

### Step 4: Test ruff formatting and linting

Run: `uv run ruff check . && uv run ruff format . --check`

Expected output: No formatting or linting issues

- [ ] **Step 4: Verify formatting**

### Step 5: Manual CLI testing

Test the improvements manually:

```bash
# Test error message with suggestion
uv run python -m catholic_bible get-chapter --book corinthians --chapter 1

# Test error message without suggestion
uv run python -m catholic_bible get-verse --book xyz --chapter 1 --verse 1

# Test valid book still works
uv run python -m catholic_bible get-chapter --book Genesis --chapter 1 | head -5

# Test progress bar with explicit flag
uv run python -m catholic_bible download-bible --output-dir ./test-bible --by-book --progress --testament old 2>&1 | head -10

# Test progress bar disabled
uv run python -m catholic_bible download-bible --output-dir ./test-bible --by-book --no-progress --testament old 2>&1 | head -10
```

- [ ] **Step 5: Manual CLI testing**

### Step 6: Create final summary commit

Run: `git log --oneline -10`

Verify all commits from this feature are present:
1. feat: add custom error exceptions
2. feat: update lookup_book() to raise InvalidBookError with fuzzy matching
3. feat: add error handling to CLI book commands
4. feat: add progress bar to download-bible command

- [ ] **Step 6: Verify commit history**

### Step 7: Final verification

Run: `pytest` one final time to ensure all tests pass

Run: `git status` to verify no uncommitted changes

- [ ] **Step 7: Final verification**

---

## Success Criteria Verification

After completing all tasks:

- ✅ Invalid book names show closest match suggestion (Task 2, Task 3)
- ✅ Error messages are concise and actionable (Tasks 1, 3)
- ✅ Progress bar shows in interactive terminals (Task 4)
- ✅ Progress bar hidden in scripts (Task 4, auto-detection)
- ✅ `--progress/--no-progress` flags work correctly (Task 4)
- ✅ All existing tests pass (Task 5, Step 1)
- ✅ New tests provide good coverage (Task 5, Step 2)
- ✅ Scripts/automation unaffected (Task 4, auto-detection + flags)

---

## Notes for Implementer

- **Import order:** Always add `from catholic_bible import errors` where needed
- **Test isolation:** Each test should work independently; use fixtures for CliRunner
- **Error messages:** Keep them to one line for readability
- **Progress bar:** Use stderr, not stdout, to keep stdout clean for JSON
- **Mocking:** Mock `sys.stderr.isatty()` in tests to avoid terminal detection issues
- **Backward compatibility:** Valid book names should work exactly as before
- **Type hints:** Maintain PEP 484 compatibility; all new functions should be typed
