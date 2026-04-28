# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
# Install dependencies and set up pre-commit hooks
uv sync
uvx pre-commit install

# Run all tests (includes mypy, ruff check, ruff format, doctests)
uv run pytest

# Run a single test file
uv run pytest tests/test_usccb.py

# Run a single test by name
uv run pytest tests/test_usccb.py::test_get_chapter

# Lint only
uv run ruff check .

# Format only
uv run ruff format .

# Type check only
uv run mypy catholic_bible tests

# Run CLI
uv run python -m catholic_bible list-books
uv run python -m catholic_bible get-chapter --book genesis --chapter 1
```

## Architecture

### Core Modules

`catholic_bible/` contains:
- `usccb.py` — Async HTTP client (`USCCB` class) + HTML parsing pipeline
- `models.py` — Immutable `NamedTuple` types: `VerseRef`, `BibleFootnote`, `BibleVerse`, `BibleSection`, `BibleChapter`, `Language` (supports English/Spanish)
- `constants.py` — All 73 Catholic canon books as typed named tuples (`OLD_TESTAMENT_BOOKS`, `NEW_TESTAMENT_BOOKS`, `ALL_BOOKS`, `BIBLE_BOOKS` dict)
- `utils.py` — `lookup_book()` and `book_url_name()` helpers
- `_io.py` — Async JSON file writer (`write_file()`)
- `__main__.py` — CLI entry point
- `commands/` — `asyncclick` CLI group and commands (`list-books`, `get-chapter`, `get-verse`, `get-book`, `download-bible`)

### HTML Parsing Pipeline

The USCCB website structure that the parser targets:
- Chapter starts at `<h3>` matching `/chapter/i`
- Verse numbers: `<span class="bcv">` inside `<a name="BBCCCVVV">` anchors
- Section headings: `<b>` or `<strong>` tags in paragraph text
- Letter footnote refs: `<a class="enref"><sup>a</sup></a>` (kept)
- Cross-ref footnotes: `<a class="fnref">` (skipped)
- Stop condition: paragraph with `class` starting with `"fn"`

The pipeline: `_iter_section_events` → `_iter_paragraph_events` → `_iter_anchor_events` yield `(event, value)` tuples, consumed by `_SectionState` accumulator into `BibleSection`/`BibleVerse` objects.

### Test Fixtures

`tests/data/genesis-chapter-1.html` — representative USCCB HTML for parser tests
`tests/data/genesis-chapter-1.json` — expected parsed output for that HTML

## Key Constraints

- `pytest` config (`pyproject.toml`) runs `--doctest-modules --mypy --ruff --ruff-format` automatically — all four checks must pass together.
- Line length: 120 characters.
- The `BibleBookInfo` import in `utils.py` carries `# noqa: TC001` because it's used in doctest examples at runtime (can't move to `TYPE_CHECKING`).
- `__all__` in `__init__.py` carries `# noqa: RUF022` because the sort order differs from isort-alphabetical (public API ordering is intentional).
- String variable names containing `token` or `type` trigger ruff S105 (hardcoded password false positive) — use `event` instead.
