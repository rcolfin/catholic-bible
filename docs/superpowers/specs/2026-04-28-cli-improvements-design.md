# CLI Improvements Design Spec

**Date:** 2026-04-28  
**Project:** catholic-bible  
**Scope:** Better error messages for invalid book names + progress reporting for `download-bible` command

---

## Overview

Improve CLI user experience by:
1. Showing helpful suggestions when users mistype book names
2. Displaying real-time download progress with book counts
3. Auto-detecting terminal interactivity to avoid breaking scripts

These changes keep users informed without breaking automation.

---

## Architecture

### New Module: `catholic_bible/errors.py`

Custom exception hierarchy for user-facing errors.

```python
class InvalidBookError(Exception):
    """Raised when a book name doesn't match any canonical book."""
    def __init__(self, book_name: str, closest_match: str | None = None):
        self.book_name = book_name
        self.closest_match = closest_match
    
    def __str__(self) -> str:
        msg = f"Book '{self.book_name}' not found"
        if self.closest_match:
            msg += f". Did you mean: {self.closest_match}?"
        return msg

class InvalidChapterError(Exception):
    """Raised when a chapter number is invalid for a book."""
    def __init__(self, book_name: str, chapter: int, max_chapters: int):
        self.book_name = book_name
        self.chapter = chapter
        self.max_chapters = max_chapters
    
    def __str__(self) -> str:
        return f"{self.book_name} has {self.max_chapters} chapters, not {self.chapter}"
```

### Modified: `catholic_bible/utils.py`

**Function: `lookup_book(query: str) -> BibleBookInfo`**

Current behavior: Returns `BibleBookInfo` or `None` if not found.

New behavior:
- Raises `InvalidBookError` if book not found
- Uses `difflib.get_close_matches(query, all_books, n=1, cutoff=0.6)` to find closest match
- Passes closest match (if found) to exception

```python
def lookup_book(query: str) -> BibleBookInfo:
    # Existing search logic...
    
    if not found:
        # Find closest match
        all_book_names = [book.name for book in constants.ALL_BOOKS]
        closest = difflib.get_close_matches(query, all_book_names, n=1, cutoff=0.6)
        closest_match = closest[0] if closest else None
        raise InvalidBookError(query, closest_match)
    
    return book_info
```

**Impact on callers:** All CLI commands that call `lookup_book()` must handle `InvalidBookError`.

### Modified: `catholic_bible/commands/bible.py`

**Error Handling in All Book-Related Commands:**

Commands `get-chapter`, `get-verse`, `get-book`, `list-books` that call `lookup_book()` wrap the call:

```python
try:
    book = utils.lookup_book(book_arg)
except errors.InvalidBookError as e:
    logger.error(str(e))
    return  # Exit with code 1
```

CLI automatically exits with code 1 due to raised exception caught by asyncclick.

**Progress Bar in `download_bible()` Command:**

Add progress reporting to the existing command:

```python
@cli.command("download-bible")
@click.option("--output-dir", required=True, ...)
@click.option("--progress/--no-progress", default=None, 
              help="Show progress bar (auto-detect if not specified).")
async def download_bible(output_dir: str, ..., progress: bool | None, ...):
    # Determine if we should show progress
    should_show_progress = progress if progress is not None else sys.stderr.isatty()
    
    # Create progress tracker if needed
    progress_tracker = None
    if should_show_progress:
        from rich.progress import Progress
        progress_tracker = Progress()
    
    # Existing download logic, updated to call progress_tracker.update()
    # Show: ████░░░░░░ 40% (30/73 books)
```

**Progress Display:**
- Uses `rich.Progress` (already in dependencies)
- Format: `[████░░░░░░] 40% (30/73 books)`
- Writes to stderr so stdout remains clean for JSON capture
- Only shown if `sys.stderr.isatty()` is `True` (interactive terminal)

**Explicit Control:**
- `--progress` forces progress bar even in non-interactive environments (useful for CI monitoring)
- `--no-progress` suppresses progress bar even in interactive terminals (for logging)
- Default (no flag) auto-detects based on terminal

---

## Components

| Component | File | Change | Purpose |
|-----------|------|--------|---------|
| `InvalidBookError` | `errors.py` | New | Exception for invalid book names |
| `InvalidChapterError` | `errors.py` | New | Reserved for future use |
| `lookup_book()` | `utils.py` | Modified | Raise `InvalidBookError` instead of returning `None` |
| `get-chapter` | `commands/bible.py` | Modified | Catch and display `InvalidBookError` |
| `get-verse` | `commands/bible.py` | Modified | Catch and display `InvalidBookError` |
| `get-book` | `commands/bible.py` | Modified | Catch and display `InvalidBookError` |
| `download-bible` | `commands/bible.py` | Modified | Add progress bar with auto-detect + explicit flags |

---

## Data Flow

### Error Message Path
```
User runs: python -m catholic_bible get-chapter --book corinthians --chapter 1
                    ↓
        CLI calls: utils.lookup_book("corinthians")
                    ↓
        lookup_book() searches constants.ALL_BOOKS
                    ↓
        No exact match found
                    ↓
        Uses difflib.get_close_matches("corinthians", all_books, n=1, cutoff=0.6)
                    ↓
        Returns: ["1 Corinthians"]
                    ↓
        Raises: InvalidBookError("corinthians", "1 Corinthians")
                    ↓
        CLI catches exception, logs error message
                    ↓
        Prints: "Error: Book 'corinthians' not found. Did you mean: 1 Corinthians?"
                    ↓
        Exits with code 1
```

### Progress Bar Path
```
User runs: python -m catholic_bible download-bible --output-dir ./bible
                    ↓
        Check sys.stderr.isatty() → True (interactive terminal)
                    ↓
        Create rich.Progress tracker
                    ↓
        For each book: increment progress bar
                    ↓
        Display: [████░░░░░░] 40% (30/73 books)
                    ↓
        Clean exit when done
```

---

## Error Handling

### Invalid Book Name
- **Trigger:** User enters book name that doesn't match any canonical book
- **Detection:** `lookup_book()` searches `constants.ALL_BOOKS`, finds no match
- **Response:** Raise `InvalidBookError` with closest match (if match >= 60% similarity)
- **User sees:** `"Error: Book 'corinthians' not found. Did you mean: 1 Corinthians?"`
- **Exit code:** 1

### No Close Match Found
- **Trigger:** User enters very different book name (e.g., `"xyz"`)
- **Response:** Raise `InvalidBookError` with `closest_match=None`
- **User sees:** `"Error: Book 'xyz' not found."`
- **Exit code:** 1

### Non-Interactive Environment (Script)
- **Trigger:** Command run with stdout/stderr piped or redirected
- **Detection:** `sys.stderr.isatty()` returns `False`
- **Response:** Progress bar not shown, command runs normally
- **User sees:** Clean JSON output to stdout, no progress artifacts
- **Exit code:** 0 (success) or 1 (error)

---

## Testing

### Unit Tests (new file: `tests/test_errors.py`)
- Test `InvalidBookError.__str__()` with and without closest match
- Test `InvalidChapterError.__str__()` with various chapter counts

### Integration Tests (modified: `tests/test_commands.py`)
- Test `get-chapter` with invalid book name → error message with suggestion
- Test `get-verse` with invalid book name → error message
- Test `get-book` with invalid book name → error message
- Test that error exit code is 1
- Test that valid books still work correctly

### Progress Bar Tests (modified: `tests/test_commands.py`)
- Test `download-bible` with `--progress` flag (force on)
- Test `download-bible` with `--no-progress` flag (force off)
- Test `download-bible` with no flag, mocked `isatty()=True` (auto show)
- Test `download-bible` with no flag, mocked `isatty()=False` (auto hide)
- Verify progress output goes to stderr, not stdout

### Fuzzy Matching Tests (modified: `tests/test_utils.py`)
- Test `lookup_book("corinthians")` raises `InvalidBookError` with closest match "1 Corinthians"
- Test `lookup_book("gen")` raises `InvalidBookError` with closest match "Genesis"
- Test `lookup_book("xyz")` raises `InvalidBookError` with closest match `None`
- Test valid book names still return `BibleBookInfo` correctly

---

## Implementation Details

### Fuzzy Matching Parameters
- **Library:** `difflib.get_close_matches()` (Python standard library)
- **n:** 1 (return single closest match)
- **cutoff:** 0.6 (60% similarity threshold)
- **Rationale:** Strict cutoff prevents suggesting unrelated books for typos like "xyz"

### Progress Bar Format
- **Library:** `rich.Progress` (already in `uv.lock`)
- **Format:** `[████░░░░░░] 40% (30/73 books)`
- **Update frequency:** After each book completes
- **Stderr:** Yes (preserves stdout for JSON)

### Backward Compatibility
- Valid CLI usage unchanged
- Scripts using valid book names unaffected
- Scripts that depended on `None` return from `lookup_book()` will break (but that's private API)
- JSON output format unchanged

---

## Scope & Limitations

**In Scope:**
- Error messages for invalid book names only
- Progress bar for `download-bible` only
- Auto-detect terminal interactivity

**Out of Scope (Future):**
- Error messages for invalid chapter/verse numbers
- Progress bars in other commands
- Custom error recovery (e.g., auto-correct)

---

## Files Changed

| File | Type | Changes |
|------|------|---------|
| `catholic_bible/errors.py` | New | Custom exception classes |
| `catholic_bible/utils.py` | Modified | `lookup_book()` raises `InvalidBookError` |
| `catholic_bible/commands/bible.py` | Modified | Error handling + progress bar in `download_bible()` |
| `tests/test_errors.py` | New | Test error message formatting |
| `tests/test_commands.py` | Modified | Test error handling and progress bar |
| `tests/test_utils.py` | Modified | Test fuzzy matching behavior |

---

## Success Criteria

- ✓ Invalid book names show closest match suggestion (or "not found" if no match)
- ✓ Error messages are concise and actionable
- ✓ Progress bar shows in interactive terminals, hidden in scripts
- ✓ `--progress/--no-progress` flags work correctly
- ✓ All existing tests pass
- ✓ New tests provide 90%+ coverage of error and progress paths
- ✓ Scripts/automation unaffected by changes (no prompts, clean error codes)
