# Cross-Reference Parsing — Design Spec

**Date:** 2026-03-24
**Status:** Approved

---

## Overview

Parse USCCB cross-reference strings (found in Bible footnotes) into structured `VerseRef` objects. A cross-reference string encodes one or more Bible verse references, potentially spanning multiple books and chapters, in a compact notation like:

```
l. [1:26–27] Gn 5:1, 3; 9:6; Ps 8:5–6; Wis 2:23; 10:2; Sir 17:1, 3–4; Mt 19:4; Mk 10:6; Jas 3:7; Eph 4:24; Col 3:10.
```

---

## Scope

- Add `VerseRef` NamedTuple to `models.py`
- Add Spanish abbreviation fields to `BibleBookInfo` in `constants.py`
- Make `lookup_book()` language-aware
- Add `parse_cross_references()` to `utils.py`
- No CLI changes (existing `get-book --save --include-intro` already covers book download)

---

## 1. Data Model — `VerseRef` (`models.py`)

```python
class VerseRef(NamedTuple):
    book: BibleBookInfo | str  # BibleBookInfo when resolved, raw abbrev string when not
    chapter: int
    start_verse: int
    end_verse: int             # == start_verse for single verses
```

`book` is `BibleBookInfo` when the abbreviation is resolved via `lookup_book()`, and the raw abbreviation string when it is not (e.g. an unknown or unsupported abbreviation). This avoids silent data loss while keeping the type non-nullable.

`to_dict()` normalises `book` to the URL name (e.g. `"psalms"`) when resolved, or keeps the raw string when not:

```python
def to_dict(self) -> dict[str, Any]:
    """
    >>> from catholic_bible.constants import BibleBookInfo
    >>> VerseRef(BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50, "Gn", "Gén"), 5, 1, 1).to_dict()
    {'book': 'genesis', 'chapter': 5, 'start_verse': 1, 'end_verse': 1}
    >>> VerseRef("UnknownBook", 1, 1, 1).to_dict()
    {'book': 'UnknownBook', 'chapter': 1, 'start_verse': 1, 'end_verse': 1}
    """
    from catholic_bible import utils
    book_val = utils.book_url_name(self.book) if isinstance(self.book, BibleBookInfo) else self.book
    return {"book": book_val, "chapter": self.chapter, "start_verse": self.start_verse, "end_verse": self.end_verse}
```

`to_dict()` always returns all four keys (`book`, `chapter`, `start_verse`, `end_verse`) — no keys are omitted, even when `end_verse == start_verse`.

`BibleBookInfo` is imported at the top of `models.py` from `catholic_bible.constants`. No circular dependency: `constants.py` does not import from `models.py`.

---

## 2. Constants — Spanish Abbreviations (`constants.py`)

`BibleBookInfo` gains two new fields:

```python
BibleBookInfo = NamedTuple("BibleBookInfo", [
    ("name", str),
    ("long_name", str),
    ("short_abbreviation", str),           # English short:  "Gn"
    ("long_abbreviation", str),            # English long:   "Gen"
    ("num_chapters", int),
    ("spanish_short_abbreviation", str),   # Spanish short:  "Gn"
    ("spanish_long_abbreviation", str),    # Spanish long:   "Gn"
])
```

All 73 book definitions in `OLD_TESTAMENT_BOOKS` and `NEW_TESTAMENT_BOOKS` are updated with their Spanish USCCB abbreviations. This is mechanical data-entry work — no logic changes elsewhere in constants.

Example entries:

| Book        | EN short | EN long | ES short | ES long |
|-------------|----------|---------|----------|---------|
| Genesis     | `Gn`     | `Gen`   | `Gn`     | `Gén`   |
| Psalms      | `Ps`     | `Ps`    | `Sal`    | `Sal`   |
| Revelation  | `Rev`    | `Rev`   | `Ap`     | `Ap`    |
| Ecclesiastes| `Eccl`   | `Eccl`  | `Qo`     | `Qo`    |

---

## 3. Lookup — Language-Aware `lookup_book()` (`utils.py`)

```python
def lookup_book(
    key: str | None,
    language: Language = Language.ENGLISH,
) -> BibleBookInfo | None:
```

`_build_book_lookup` is updated to accept a `language` parameter and index the correct abbreviation fields (`short_abbreviation`/`long_abbreviation` for English, `spanish_short_abbreviation`/`spanish_long_abbreviation` for Spanish). The cached `_get_old_testament_book_lookup()` / `_get_new_testament_book_lookup()` helpers become per-language (or the cache key incorporates language).

The cached helper functions `_get_old_testament_book_lookup()` / `_get_new_testament_book_lookup()` become language-aware by adding a `language: Language` parameter and changing `@lru_cache(maxsize=1)` to `@lru_cache(maxsize=2)` — one cache slot per language per testament (4 slots total across 2 functions × 2 languages).

Existing call-sites that pass no `language` argument continue to work unchanged.

---

## 4. Parser — `parse_cross_references()` (`utils.py`)

```python
def parse_cross_references(
    text: str,
    language: Language = Language.ENGLISH,
) -> list[VerseRef]:
```

### Input format

```
l. [1:26–27] Gn 5:1, 3; 9:6; Ps 8:5–6; Wis 2:23; 10:2; Sir 17:1, 3–4; Mt 19:4; Mk 10:6; Jas 3:7; Eph 4:24; Col 3:10.
```

- Footnote letter prefix: `l.` (single letter + period)
- Optional source context: `[chapter:verse–verse]` (where the footnote appears — discarded)
- Reference list: `;`-separated groups, trailing period stripped

### Parsing algorithm

1. **Strip prefix:** remove leading `<letter>.\s*` and optional `\[...\]\s*` context block.
2. **Strip trailing period.**
3. **Split by `;`**, trim whitespace from each group.
4. **For each group:**
   - Split on first whitespace. If the first token contains no `:`, treat it as a book abbreviation token; call `lookup_book(token, language)`. If resolved, update `current_book`. If not resolved, set `current_book = token` (raw string).
   - If the first token contains `:`, no book change — carry `current_book` forward.
5. **Split remaining text by `,`**, trim each item.
6. **For each item:**
   - If it contains `:`, parse as `chapter:verse_part`. Update `current_chapter`.
   - Otherwise, parse as `verse_part` for `current_chapter`.
   - `verse_part` is either `N` (single verse) or `N–M` / `N-M` (range, en-dash or hyphen).
   - Emit `VerseRef(current_book, current_chapter, start_verse, end_verse)`.

### Traced example

Input (after prefix strip): `Gn 5:1, 3; 9:6; Ps 8:5–6; Wis 2:23; 10:2; Sir 17:1, 3–4`

| Group        | Book    | Chapter | Item  | start | end | VerseRef                    |
|--------------|---------|---------|-------|-------|-----|-----------------------------|
| `Gn 5:1, 3`  | genesis | 5       | `5:1` | 1     | 1   | (genesis, 5, 1, 1)          |
|              | genesis | 5       | `3`   | 3     | 3   | (genesis, 5, 3, 3)          |
| `9:6`        | genesis | 9       | `9:6` | 6     | 6   | (genesis, 9, 6, 6)          |
| `Ps 8:5–6`   | psalms  | 8       | `8:5–6` | 5   | 6   | (psalms, 8, 5, 6)           |
| `Wis 2:23`   | wisdom  | 2       | `2:23`| 23    | 23  | (wisdom, 2, 23, 23)         |
| `10:2`       | wisdom  | 10      | `10:2`| 2     | 2   | (wisdom, 10, 2, 2)          |
| `Sir 17:1, 3–4` | sirach | 17    | `17:1`| 1     | 1   | (sirach, 17, 1, 1)          |
|              | sirach  | 17      | `3–4` | 3     | 4   | (sirach, 17, 3, 4)          |

### Edge cases

- En-dash (`–`, U+2013) and hyphen (`-`) both treated as range separators.
- Unresolvable book abbreviation → `current_book = raw string`, parsing continues.
- Items that cannot be parsed as integers (i.e. `int(verse_str)` raises `ValueError`) are logged as warnings and skipped — the offending item is dropped but parsing of subsequent items continues.
- Empty groups (e.g. trailing `;`) are ignored.

---

## 5. Testing

- **`tests/test_utils.py`** — unit tests for `parse_cross_references`:
  - Full example from the spec (multi-book, ranges, chapter-carry, book-carry)
  - Single verse
  - Verse range
  - Book-carry across groups
  - Chapter-carry within a group
  - Unresolved abbreviation falls back to raw string
  - Spanish language input (`Sal 8:5–6` → psalms)
- **`tests/test_models.py`** — `VerseRef.to_dict()` for resolved and unresolved book
- Doctests on `parse_cross_references` and `VerseRef.to_dict()`

---

## Out of Scope

- Formatting `VerseRef` back to citation string
- Attaching parsed cross-references to `BibleFootnote` (future work)
- CLI changes (`get-book --save --include-intro` already covers book download)
