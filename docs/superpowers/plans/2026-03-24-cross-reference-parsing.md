# Cross-Reference Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse USCCB cross-reference strings (e.g. `l. [1:26–27] Gn 5:1, 3; 9:6; Ps 8:5–6`) into a structured list of `VerseRef` objects with book, chapter, start/end verse.

**Architecture:** Add `VerseRef` NamedTuple to `models.py`, extend `BibleBookInfo` with Spanish abbreviation fields (two new NamedTuple fields with defaults), make `lookup_book()` language-aware, and add a stateful `parse_cross_references()` parser to `utils.py`. The parser strips the footnote prefix, walks `;`-separated groups maintaining book/chapter state, and handles comma-separated verse items and en-dash ranges.

**Tech Stack:** Python 3.12+, `NamedTuple`, `re`, `lru_cache`, `pytest` (with `--doctest-modules --mypy --ruff --ruff-format`), `uv`

---

## File Map

| File | Change |
|------|--------|
| `catholic_bible/constants.py` | Add `spanish_short_abbreviation`, `spanish_long_abbreviation` fields to `BibleBookInfo`; update all 73 entries |
| `catholic_bible/models.py` | Add `VerseRef` NamedTuple; import `BibleBookInfo` from constants |
| `catholic_bible/utils.py` | Add `language` parameter to `lookup_book`, `_build_book_lookup`, helper functions; add `parse_cross_references` |
| `catholic_bible/__init__.py` | Export `VerseRef` |
| `tests/test_utils.py` | Update `BibleBookInfo` constructions (new fields have defaults — no change needed); add `parse_cross_references` tests |
| `tests/test_models.py` | Add `VerseRef.to_dict()` tests |

---

## Spanish Abbreviations Reference

All 73 books with their Spanish USCCB abbreviations. Use these when updating `constants.py`. Verify against [https://bible.usccb.org/es/bible/](https://bible.usccb.org/es/bible/) if in doubt.

### Old Testament (46 books)

| Book | ES short | ES long |
|------|----------|---------|
| Genesis | `Gn` | `Gén` |
| Exodus | `Ex` | `Éx` |
| Leviticus | `Lv` | `Lev` |
| Numbers | `Nm` | `Núm` |
| Deuteronomy | `Dt` | `Deut` |
| Joshua | `Jos` | `Jos` |
| Judges | `Jue` | `Jue` |
| Ruth | `Rt` | `Rut` |
| 1 Samuel | `1Sm` | `1Sam` |
| 2 Samuel | `2Sm` | `2Sam` |
| 1 Kings | `1Re` | `1Re` |
| 2 Kings | `2Re` | `2Re` |
| 1 Chronicles | `1Cr` | `1Cro` |
| 2 Chronicles | `2Cr` | `2Cro` |
| Ezra | `Esd` | `Esd` |
| Nehemiah | `Ne` | `Neh` |
| Tobit | `Tb` | `Tob` |
| Judith | `Jdt` | `Jdt` |
| Esther | `Est` | `Est` |
| 1 Maccabees | `1Mac` | `1Mac` |
| 2 Maccabees | `2Mac` | `2Mac` |
| Job | `Jb` | `Job` |
| Psalms | `Sal` | `Sal` |
| Proverbs | `Pr` | `Prov` |
| Ecclesiastes | `Qo` | `Qoh` |
| Song of Songs | `Ct` | `Cant` |
| Wisdom | `Sab` | `Sab` |
| Sirach | `Si` | `Sir` |
| Isaiah | `Is` | `Is` |
| Jeremiah | `Jr` | `Jer` |
| Lamentations | `Lm` | `Lam` |
| Baruch | `Ba` | `Bar` |
| Ezekiel | `Ez` | `Ezeq` |
| Daniel | `Dn` | `Dan` |
| Hosea | `Os` | `Os` |
| Joel | `Jl` | `Joel` |
| Amos | `Am` | `Amós` |
| Obadiah | `Ab` | `Abd` |
| Jonah | `Jon` | `Jon` |
| Micah | `Mi` | `Miq` |
| Nahum | `Na` | `Nah` |
| Habakkuk | `Hb` | `Hab` |
| Zephaniah | `So` | `Sof` |
| Haggai | `Ag` | `Ag` |
| Zechariah | `Za` | `Zac` |
| Malachi | `Ml` | `Mal` |

### New Testament (27 books)

| Book | ES short | ES long |
|------|----------|---------|
| Matthew | `Mt` | `Mt` |
| Mark | `Mc` | `Mc` |
| Luke | `Lc` | `Lc` |
| John | `Jn` | `Jn` |
| Acts | `Hch` | `Hch` |
| Romans | `Rm` | `Rom` |
| 1 Corinthians | `1Co` | `1Cor` |
| 2 Corinthians | `2Co` | `2Cor` |
| Galatians | `Ga` | `Gál` |
| Ephesians | `Ef` | `Ef` |
| Philippians | `Flp` | `Flp` |
| Colossians | `Col` | `Col` |
| 1 Thessalonians | `1Ts` | `1Tes` |
| 2 Thessalonians | `2Ts` | `2Tes` |
| 1 Timothy | `1Tm` | `1Tim` |
| 2 Timothy | `2Tm` | `2Tim` |
| Titus | `Tt` | `Tit` |
| Philemon | `Flm` | `Flm` |
| Hebrews | `Hb` | `Heb` |
| James | `Sant` | `Sant` |
| 1 Peter | `1Pe` | `1Pe` |
| 2 Peter | `2Pe` | `2Pe` |
| 1 John | `1Jn` | `1Jn` |
| 2 John | `2Jn` | `2Jn` |
| 3 John | `3Jn` | `3Jn` |
| Jude | `Jds` | `Jds` |
| Revelation | `Ap` | `Ap` |

---

## Task 1: Add Spanish Abbreviation Fields to `BibleBookInfo`

**Files:**
- Modify: `catholic_bible/constants.py`

### Context

`BibleBookInfo` is a `NamedTuple` with 5 fields. Add two new fields **with defaults** so existing constructions (in tests, doctests, and user code) do not break. An empty string default signals "not populated" and will be skipped in the lookup builder.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_utils.py`:

```python
def test_lookup_book_spanish_psalms() -> None:
    from catholic_bible.models import Language
    result = lookup_book("Sal", Language.SPANISH)
    assert result is not None
    assert result.name == "Psalms"


def test_lookup_book_spanish_revelation() -> None:
    from catholic_bible.models import Language
    result = lookup_book("Ap", Language.SPANISH)
    assert result is not None
    assert result.name == "Revelation"
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_utils.py::test_lookup_book_spanish_psalms -v
```

Expected: `TypeError` or `FAILED` — `lookup_book` does not yet accept a `language` argument.

- [ ] **Step 3: Update `BibleBookInfo` in `constants.py`**

Change the class definition to:

```python
class BibleBookInfo(NamedTuple):
    """Metadata for a book of the Bible."""

    name: str
    """The full display name (e.g. 'Genesis', '1 Corinthians')."""
    title: str
    """The liturgical title (e.g. 'Book of Genesis')."""
    short_abbreviation: str
    """The short abbreviation used in verse references (e.g. 'Gn')."""
    long_abbreviation: str
    """The long abbreviation used in verse references (e.g. 'Gen')."""
    num_chapters: int
    """The number of chapters in this book."""
    spanish_short_abbreviation: str = ""
    """The Spanish short abbreviation (e.g. 'Sal' for Psalms). Empty if not yet populated."""
    spanish_long_abbreviation: str = ""
    """The Spanish long abbreviation (e.g. 'Sal' for Psalms). Empty if not yet populated."""
```

- [ ] **Step 4: Update all 73 book entries in `constants.py`**

Add the two Spanish abbreviation arguments (positionally) to every `BibleBookInfo(...)` call. Use the table above. Example:

```python
# Before
Genesis=BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50),
Psalms=BibleBookInfo("Psalms", "Book of Psalms", "Ps", "Psalms", 150),
Revelation=BibleBookInfo("Revelation", "Book of Revelation", "Rv", "Rev", 22),

# After
Genesis=BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50, "Gn", "Gén"),
Psalms=BibleBookInfo("Psalms", "Book of Psalms", "Ps", "Psalms", 150, "Sal", "Sal"),
Revelation=BibleBookInfo("Revelation", "Book of Revelation", "Rv", "Rev", 22, "Ap", "Ap"),
```

Do this for all 73 books using the reference table above.

- [ ] **Step 5: Run the full suite to confirm only the new test fails (due to missing language param)**

```bash
uv run pytest
```

Expected: all existing tests pass; the two new Spanish tests fail with `TypeError`.

- [ ] **Step 6: Commit**

```bash
git add catholic_bible/constants.py tests/test_utils.py
git commit -m "feat: add Spanish abbreviation fields to BibleBookInfo"
```

---

## Task 2: Make `lookup_book()` Language-Aware

**Files:**
- Modify: `catholic_bible/utils.py`

### Context

Add a `language: Language = Language.ENGLISH` parameter to `lookup_book` and the two cached helper functions. Update `_build_book_lookup` to index the correct abbreviation fields based on language. Change `@lru_cache(maxsize=1)` to `@lru_cache(maxsize=2)` so both language variants are cached.

`Language` must be imported — add it to the imports section. It lives in `catholic_bible.models`.

- [ ] **Step 1: Add `Language` import to `utils.py`**

Add to the imports block (after existing imports):

```python
from catholic_bible.models import Language  # noqa: TC001
```

Wait — this import is used at runtime (as a default parameter value), so it cannot go under `TYPE_CHECKING`. It doesn't need `# noqa: TC001`. Just add:

```python
from catholic_bible.models import Language
```

Check for circular imports: `utils.py` → `models.py` → `constants.py` (no cycle). ✓

- [ ] **Step 2: Update `_build_book_lookup` to accept `language`**

Replace the function signature and add language-conditional abbreviation indexing:

```python
def _build_book_lookup(
    books: Iterable[BibleBookInfo], language: Language = Language.ENGLISH
) -> dict[str, BibleBookInfo]:
    lookup: dict[str, BibleBookInfo] = {}
    abbrev_lookup: dict[str, list[BibleBookInfo]] = defaultdict(list)

    for book in books:
        name = book.name.casefold()
        long_abbrev = book.long_abbreviation.casefold()
        short_abbrev = book.short_abbreviation.casefold()
        url_name = book_url_name(book).casefold()

        assert long_abbrev not in lookup, f"{long_abbrev} already exists."  # noqa: S101
        assert name not in lookup, f"{name} already exists."  # noqa: S101

        lookup[long_abbrev] = book
        lookup[name] = book
        lookup[url_name] = book

        if " " in name:
            lookup[name.replace(" ", "")] = book

        if language == Language.SPANISH:
            if book.spanish_short_abbreviation:
                abbrev_lookup[book.spanish_short_abbreviation.casefold()].append(book)
            if book.spanish_long_abbreviation and book.spanish_long_abbreviation != book.spanish_short_abbreviation:
                abbrev_lookup[book.spanish_long_abbreviation.casefold()].append(book)
        else:
            abbrev_lookup[short_abbrev].append(book)

    for abbrev, book_list in abbrev_lookup.items():
        if len(book_list) > 1:
            logger.info("Skipping ambiguous abbreviation: %s", abbrev)
            continue
        lookup[abbrev] = book_list[0]

    return lookup
```

- [ ] **Step 3: Update the two cached helper functions**

```python
@lru_cache(maxsize=2)
def _get_old_testament_book_lookup(language: Language = Language.ENGLISH) -> dict[str, BibleBookInfo]:
    """Returns a lookup dict for Old Testament books."""
    return _build_book_lookup(constants.OLD_TESTAMENT_BOOKS, language)


@lru_cache(maxsize=2)
def _get_new_testament_book_lookup(language: Language = Language.ENGLISH) -> dict[str, BibleBookInfo]:
    """Returns a lookup dict for New Testament books."""
    return _build_book_lookup(constants.NEW_TESTAMENT_BOOKS, language)
```

- [ ] **Step 4: Update `lookup_book` signature**

```python
def lookup_book(
    key: str | None,
    language: Language = Language.ENGLISH,
) -> BibleBookInfo | None:
    """
    Looks up a book by name, URL name, or abbreviation (case-insensitive).

    >>> lookup_book("genesis").name
    'Genesis'
    >>> lookup_book("Genesis").name
    'Genesis'
    >>> lookup_book("1corinthians").name
    '1 Corinthians'
    >>> lookup_book("Gen").name
    'Genesis'
    >>> lookup_book("Gn").name
    'Genesis'
    >>> lookup_book(None) is None
    True
    >>> lookup_book("notabook") is None
    True
    """
    if key is None:
        return None

    key = key.replace(" ", "").strip().casefold()
    ot_lookup = _get_old_testament_book_lookup(language)
    nt_lookup = _get_new_testament_book_lookup(language)
    ot_book = ot_lookup.get(key)
    nt_book = nt_lookup.get(key)

    if ot_book:
        if nt_book:
            logger.warning("Ambiguous book key '%s' matches both testaments.", key)
            return None
        return ot_book

    return nt_book
```

- [ ] **Step 5: Run the new tests to verify they pass**

```bash
uv run pytest tests/test_utils.py -v
```

Expected: all pass, including the two new Spanish tests.

- [ ] **Step 6: Run the full suite**

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add catholic_bible/utils.py
git commit -m "feat: make lookup_book language-aware with Spanish abbreviation support"
```

---

## Task 3: Add `VerseRef` to `models.py`

**Files:**
- Modify: `catholic_bible/models.py`
- Modify: `catholic_bible/__init__.py`
- Modify: `tests/test_models.py`

### Context

`VerseRef` stores a single resolved verse reference. `book` is `BibleBookInfo` when the abbreviation was resolved, or a raw string when it was not. `to_dict()` normalises both cases to a URL name string. Import `BibleBookInfo` at the top of `models.py` — no circular dependency since `constants.py` does not import from `models.py`. Add `# noqa: TC001` because the import is needed at runtime (isinstance check in `to_dict`).

- [ ] **Step 1: Write failing tests**

Add to `tests/test_models.py`:

```python
from catholic_bible.models import BibleFootnote, BibleChapter, BibleSection, BibleVerse, Language, VerseRef
from catholic_bible.constants import BibleBookInfo


def test_verse_ref_to_dict_resolved() -> None:
    book = BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50, "Gn", "Gén")
    ref = VerseRef(book, 5, 1, 1)
    assert ref.to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 1, "end_verse": 1}


def test_verse_ref_to_dict_range() -> None:
    book = BibleBookInfo("Psalms", "Book of Psalms", "Ps", "Psalms", 150, "Sal", "Sal")
    ref = VerseRef(book, 8, 5, 6)
    assert ref.to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}


def test_verse_ref_to_dict_unresolved() -> None:
    ref = VerseRef("UnknownBook", 1, 1, 1)
    assert ref.to_dict() == {"book": "UnknownBook", "chapter": 1, "start_verse": 1, "end_verse": 1}


def test_verse_ref_to_dict_always_includes_end_verse() -> None:
    book = BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50, "Gn", "Gén")
    ref = VerseRef(book, 1, 3, 3)
    d = ref.to_dict()
    assert "end_verse" in d
    assert d["end_verse"] == 3
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_models.py::test_verse_ref_to_dict_resolved -v
```

Expected: `ImportError` — `VerseRef` does not exist yet.

- [ ] **Step 3: Add `VerseRef` to `models.py`**

Add this import near the top of `models.py` (after the existing imports, before `_REPR_MAX_LEN`):

```python
from catholic_bible.constants import BibleBookInfo  # noqa: TC001
```

Add the `VerseRef` class **before** `BibleFootnote`:

```python
class VerseRef(NamedTuple):
    """A single resolved Bible verse reference from a cross-reference string."""

    book: BibleBookInfo | str
    """The book, either as a resolved BibleBookInfo or raw abbreviation string if unresolved."""
    chapter: int
    """The chapter number."""
    start_verse: int
    """The first verse in the range (or the only verse for a single reference)."""
    end_verse: int
    """The last verse in the range. Equal to start_verse for single-verse references."""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation with all four keys always present.

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

- [ ] **Step 4: Export `VerseRef` from `__init__.py`**

```python
# In catholic_bible/__init__.py, update the import:
from catholic_bible.models import VerseRef

# Add to __all__:
__all__ = ["BibleBookInfo", "USCCB", "VerseRef", "__version__", "constants", "models"]  # noqa: RUF022
```

- [ ] **Step 5: Run the new tests**

```bash
uv run pytest tests/test_models.py -v
```

Expected: all pass.

- [ ] **Step 6: Run the full suite**

```bash
uv run pytest
```

Expected: all tests pass, including doctests.

- [ ] **Step 7: Commit**

```bash
git add catholic_bible/models.py catholic_bible/__init__.py tests/test_models.py
git commit -m "feat: add VerseRef model to models.py"
```

---

## Task 4: Implement `parse_cross_references()`

**Files:**
- Modify: `catholic_bible/utils.py`
- Modify: `tests/test_utils.py`

### Context

`parse_cross_references` takes a raw USCCB footnote cross-reference string and returns a list of `VerseRef` objects. The algorithm is stateful: it tracks `current_book` and `current_chapter` across `;`-separated groups.

**Input format:**
```
l. [1:26–27] Gn 5:1, 3; 9:6; Ps 8:5–6; Wis 2:23; 10:2; Sir 17:1, 3–4; Mt 19:4; Mk 10:6; Jas 3:7; Eph 4:24; Col 3:10.
```

Components:
1. Footnote letter prefix: `l.` — single letter + period (strip it)
2. Optional source context: `[1:26–27]` — bracketed, discard
3. Reference list — `;` separated, trailing period stripped

**Parsing algorithm:**
1. Strip leading `<letter>.\s*` then optional `\[.*?\]\s*`
2. Strip trailing `.`
3. Split by `;`, skip empty groups
4. For each group: if the first token (split on first space, or the whole group) contains no `:`, it's a book abbreviation → call `lookup_book(token, language)`, update `current_book` (raw string if unresolved). Remove it from the group before processing verse items.
5. Split remaining text by `,`, trim each item
6. For each item: if it contains `:`, parse `chapter:verse_part` and update `current_chapter`. Otherwise it's `verse_part` only, use `current_chapter`. Parse `verse_part` as `N` (single) or `N–M`/`N-M` (range). Emit `VerseRef`.

**Edge cases:**
- Both `–` (U+2013 en-dash) and `-` (hyphen) are range separators
- Unresolvable abbreviation: `current_book = raw_token` (str), parsing continues
- Non-integer verse strings: log warning and skip that item
- `current_book` is `None` at start; if a verse item appears before any book is set, skip it with a warning

- [ ] **Step 1: Write failing tests**

Add to `tests/test_utils.py`:

```python
from catholic_bible.models import Language, VerseRef
from catholic_bible.utils import parse_cross_references


def test_parse_cross_references_full_example() -> None:
    text = "l. [1:26\u201327] Gn 5:1, 3; 9:6; Ps 8:5\u20136; Wis 2:23; 10:2; Sir 17:1, 3\u20134; Mt 19:4; Mk 10:6; Jas 3:7; Eph 4:24; Col 3:10."
    refs = parse_cross_references(text)
    assert len(refs) == 13  # noqa: PLR2004
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 1, "end_verse": 1}
    assert refs[1].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 3, "end_verse": 3}
    assert refs[2].to_dict() == {"book": "genesis", "chapter": 9, "start_verse": 6, "end_verse": 6}
    assert refs[3].to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}
    assert refs[4].to_dict() == {"book": "wisdom", "chapter": 2, "start_verse": 23, "end_verse": 23}
    assert refs[5].to_dict() == {"book": "wisdom", "chapter": 10, "start_verse": 2, "end_verse": 2}
    assert refs[6].to_dict() == {"book": "sirach", "chapter": 17, "start_verse": 1, "end_verse": 1}
    assert refs[7].to_dict() == {"book": "sirach", "chapter": 17, "start_verse": 3, "end_verse": 4}
    assert refs[8].to_dict() == {"book": "matthew", "chapter": 19, "start_verse": 4, "end_verse": 4}
    assert refs[9].to_dict() == {"book": "mark", "chapter": 10, "start_verse": 6, "end_verse": 6}
    assert refs[10].to_dict() == {"book": "james", "chapter": 3, "start_verse": 7, "end_verse": 7}
    assert refs[11].to_dict() == {"book": "ephesians", "chapter": 4, "start_verse": 24, "end_verse": 24}
    assert refs[12].to_dict() == {"book": "colossians", "chapter": 3, "start_verse": 10, "end_verse": 10}


def test_parse_cross_references_single_verse() -> None:
    refs = parse_cross_references("a. Gn 1:1.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 1, "start_verse": 1, "end_verse": 1}


def test_parse_cross_references_verse_range() -> None:
    refs = parse_cross_references("b. Ps 8:5\u20136.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}


def test_parse_cross_references_book_carry() -> None:
    refs = parse_cross_references("c. Gn 1:1; 2:3.")
    assert len(refs) == 2  # noqa: PLR2004
    assert refs[0].to_dict()["book"] == "genesis"
    assert refs[1].to_dict()["book"] == "genesis"
    assert refs[1].to_dict()["chapter"] == 2  # noqa: PLR2004  (not 1)


def test_parse_cross_references_chapter_carry() -> None:
    refs = parse_cross_references("d. Gn 5:1, 3.")
    assert len(refs) == 2  # noqa: PLR2004
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 1, "end_verse": 1}
    assert refs[1].to_dict() == {"book": "genesis", "chapter": 5, "start_verse": 3, "end_verse": 3}


def test_parse_cross_references_unresolved_book() -> None:
    refs = parse_cross_references("e. Xyz 1:1.")
    assert len(refs) == 1
    assert refs[0].book == "Xyz"
    assert refs[0].to_dict()["book"] == "Xyz"


def test_parse_cross_references_hyphen_range() -> None:
    refs = parse_cross_references("f. Gn 1:1-3.")
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "genesis", "chapter": 1, "start_verse": 1, "end_verse": 3}


def test_parse_cross_references_spanish() -> None:
    refs = parse_cross_references("a. Sal 8:5\u20136.", Language.SPANISH)
    assert len(refs) == 1
    assert refs[0].to_dict() == {"book": "psalms", "chapter": 8, "start_verse": 5, "end_verse": 6}
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_utils.py::test_parse_cross_references_single_verse -v
```

Expected: `ImportError` — `parse_cross_references` not yet defined.

- [ ] **Step 3: Add `parse_cross_references` to `utils.py`**

Add near the top of `utils.py` (after existing imports):

```python
from catholic_bible.models import VerseRef  # noqa: TC001
```

Add a module-level regex constant (after `_FOOTNOTE_ID_PATTERN`):

```python
_CROSS_REF_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z*]\.\s*(?:\[.*?\]\s*)?",
    re.IGNORECASE,
)
_VERSE_RANGE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+)[–\-](\d+)")
```

Add the function:

```python
def parse_cross_references(
    text: str,
    language: Language = Language.ENGLISH,
) -> list[VerseRef]:
    """Parses a USCCB cross-reference string into a list of VerseRef objects.

    Strips the leading footnote letter and optional source context, then walks
    semicolon-separated groups maintaining current book and chapter state.

    Args:
        text: A raw USCCB cross-reference string,
            e.g. ``"l. [1:26\\u201327] Gn 5:1, 3; 9:6; Ps 8:5\\u20136."``.
        language: The language of the abbreviations in ``text`` (default ENGLISH).

    Returns:
        Ordered list of VerseRef objects.

    >>> refs = parse_cross_references("a. Gn 1:1.")
    >>> refs[0].to_dict()
    {'book': 'genesis', 'chapter': 1, 'start_verse': 1, 'end_verse': 1}
    >>> refs = parse_cross_references("b. Gn 5:1, 3.")
    >>> refs[0].to_dict()
    {'book': 'genesis', 'chapter': 5, 'start_verse': 1, 'end_verse': 1}
    >>> refs[1].to_dict()
    {'book': 'genesis', 'chapter': 5, 'start_verse': 3, 'end_verse': 3}
    """
    text = _CROSS_REF_PREFIX_PATTERN.sub("", text).rstrip(".")
    result: list[VerseRef] = []
    current_book: BibleBookInfo | str | None = None
    current_chapter: int | None = None

    for group in text.split(";"):
        group = group.strip()
        if not group:
            continue

        # Detect a book abbreviation: first token has no ':'
        parts = group.split(None, 1)
        if parts and ":" not in parts[0]:
            token = parts[0]
            resolved = lookup_book(token, language)
            current_book = resolved if resolved is not None else token
            group = parts[1] if len(parts) > 1 else ""

        if current_book is None:
            logger.warning("Cross-reference group has no book context, skipping: %r", group)
            continue

        for item in group.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                if ":" in item:
                    ch_str, verse_part = item.split(":", 1)
                    current_chapter = int(ch_str.strip())
                else:
                    verse_part = item

                if current_chapter is None:
                    logger.warning("Cross-reference item has no chapter context, skipping: %r", item)
                    continue

                range_match = _VERSE_RANGE_PATTERN.match(verse_part.strip())
                if range_match:
                    start_verse = int(range_match.group(1))
                    end_verse = int(range_match.group(2))
                else:
                    start_verse = int(verse_part.strip())
                    end_verse = start_verse

                result.append(VerseRef(current_book, current_chapter, start_verse, end_verse))
            except ValueError:
                logger.warning("Could not parse cross-reference item: %r", item)

    return result
```

- [ ] **Step 4: Run the new tests**

```bash
uv run pytest tests/test_utils.py -v -k "cross_ref"
```

Expected: all 8 new tests pass.

- [ ] **Step 5: Run the full suite**

```bash
uv run pytest
```

Expected: all tests pass, including mypy, ruff, ruff-format, and doctests.

- [ ] **Step 6: Commit**

```bash
git add catholic_bible/utils.py tests/test_utils.py
git commit -m "feat: add parse_cross_references() to utils.py"
```

---

## Task 5: Final Verification

- [ ] **Step 1: Run the complete test suite one final time**

```bash
uv run pytest -v
```

Expected: all tests pass — including mypy type checks, ruff lint, ruff format, and doctests.

- [ ] **Step 2: Smoke-test the parser manually**

```bash
uv run python -c "
from catholic_bible.utils import parse_cross_references
refs = parse_cross_references('l. [1:26\u201327] Gn 5:1, 3; 9:6; Ps 8:5\u20136; Wis 2:23; 10:2; Sir 17:1, 3\u20134; Mt 19:4; Mk 10:6; Jas 3:7; Eph 4:24; Col 3:10.')
for r in refs:
    print(r.to_dict())
"
```

Expected output:
```
{'book': 'genesis', 'chapter': 5, 'start_verse': 1, 'end_verse': 1}
{'book': 'genesis', 'chapter': 5, 'start_verse': 3, 'end_verse': 3}
{'book': 'genesis', 'chapter': 9, 'start_verse': 6, 'end_verse': 6}
{'book': 'psalms', 'chapter': 8, 'start_verse': 5, 'end_verse': 6}
{'book': 'wisdom', 'chapter': 2, 'start_verse': 23, 'end_verse': 23}
{'book': 'wisdom', 'chapter': 10, 'start_verse': 2, 'end_verse': 2}
{'book': 'sirach', 'chapter': 17, 'start_verse': 1, 'end_verse': 1}
{'book': 'sirach', 'chapter': 17, 'start_verse': 3, 'end_verse': 4}
{'book': 'matthew', 'chapter': 19, 'start_verse': 4, 'end_verse': 4}
{'book': 'mark', 'chapter': 10, 'start_verse': 6, 'end_verse': 6}
{'book': 'colossians', 'chapter': 3, 'start_verse': 10, 'end_verse': 10}
```

- [ ] **Step 3: Commit**

```bash
git add -p  # confirm nothing unintended is staged
git commit -m "chore: verify cross-reference parsing implementation complete"
```
