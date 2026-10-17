# catholic-bible

[![CI Build](https://github.com/rcolfin/catholic-bible/actions/workflows/ci.yml/badge.svg)](https://github.com/rcolfin/catholic-bible/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/rcolfin/catholic-bible.svg)](https://github.com/rcolfin/catholic-bible/blob/main/LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/catholic-bible)](https://pypi.python.org/pypi/catholic-bible)
[![versions](https://img.shields.io/pypi/pyversions/catholic-bible.svg)](https://github.com/rcolfin/catholic-bible)

Provides an API for scraping the [USCCB Bible](https://bible.usccb.org/bible/) website
of the United States Conference of Catholic Bishops, returning structured verse data in
both English and Spanish.

## About catholic-bible

This package facilitates pulling books, chapters, and individual verses from the Catholic
Bible. Please open new issues for any bugs you find — support is greatly appreciated!
If you have a new feature, feel free to open a pull request.

## Installation

To install [catholic-bible](https://pypi.org/project/catholic-bible/) from PyPI:

    $ pip install catholic-bible

To install from source as editable:

    $ pip install -e .

### JavaScript challenge (optional browser support)

The USCCB site sometimes answers with a "Checking connection" page that requires JavaScript to pass.
When that happens, a browser is driven through [Playwright](https://playwright.dev/python/) to pass the
challenge once, and its cookie is reused for the rest of the requests. Playwright is an optional dependency:

    $ pip install 'catholic-bible[browser]'

Without it, a `catholic_bible.challenge.ChallengeError` is raised when the challenge is encountered.

The browser can be obtained in one of three ways, configured with environment variables or the matching CLI options
(which take precedence over the environment variables):

| Environment variable | CLI option | Description |
| --- | --- | --- |
| *(none)* | | Launch Playwright's bundled headless Chromium (requires `playwright install chromium`). |
| `CATHOLIC_BIBLE_BROWSER_CHANNEL` | `--browser-channel` | Launch an installed browser instead (`chrome`, `msedge`, ...). |
| `CATHOLIC_BIBLE_BROWSER_CDP_URL` | `--browser-cdp-url` | Connect to an already running Chromium-based browser over the Chrome DevTools Protocol. |
| `CATHOLIC_BIBLE_BROWSER_WS_ENDPOINT` | `--browser-ws-endpoint` | Connect to a [Playwright server](https://playwright.dev/docs/docker#remote-connection). |
| `CATHOLIC_BIBLE_BROWSER_HEADLESS` | `--browser-headless/--browser-headed` | Whether a launched browser is headless (default: `true`). |
| `CATHOLIC_BIBLE_BROWSER_TIMEOUT` | `--browser-timeout` | Seconds to wait for the challenge (default: `30`). |
| `CATHOLIC_BIBLE_BROWSER_COOKIE_CACHE` | `--browser-cookie-cache` | File in which to save the challenge cookie so separate runs reuse it until it expires (about 30 minutes). |

#### Docker

The simplest image installs a browser alongside the package (larger, but self-contained):

```dockerfile
FROM python:3.13-slim
RUN pip install --no-cache-dir 'catholic-bible[browser]' \
    && playwright install --with-deps chromium
# Optional: reuse the challenge cookie across runs (mount a volume at /cache).
ENV CATHOLIC_BIBLE_BROWSER_COOKIE_CACHE=/cache/cookies.json
ENTRYPOINT ["python", "-m", "catholic_bible"]
```

```sh
docker build -t catholic-bible .
docker run --rm -v catholic-bible-cache:/cache catholic-bible get-chapter --book genesis --chapter 1
```

Connecting to a running browser instead means the image only needs the `playwright` Python package
(`pip install 'catholic-bible[browser]'`, without `playwright install`), not a browser:

```sh
# Use Chrome running on the host (e.g. Windows), started with remote debugging enabled:
#   chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-cdp
docker run --rm -e CATHOLIC_BIBLE_BROWSER_CDP_URL=http://<host-ip>:9222 ...

# Or use a Playwright server container alongside it (match the Playwright version):
docker run -p 3000:3000 mcr.microsoft.com/playwright:v1.64.0-noble \
    npx -y playwright@1.64.0 run-server --port 3000 --host 0.0.0.0
docker run --rm -e CATHOLIC_BIBLE_BROWSER_WS_ENDPOINT=ws://<playwright-host>:3000/ ...
```

Notes on connecting over CDP:

* Use an IP address in the CDP URL. Chrome rejects DevTools requests whose `Host` is a name other than
  `localhost`, and `localhost` itself may first resolve to IPv6, adding a long delay (use `127.0.0.1`).
* Chrome only listens on `127.0.0.1`, so reaching it from a container or another machine needs a port forward
  (e.g. `netsh interface portproxy` on Windows).
* Anyone who can reach the debugging port has full control of that browser profile. Use a dedicated
  `--user-data-dir` and don't expose the port beyond the machines that need it.

See the [browser and Docker documentation](https://rcolfin.github.io/catholic-bible/browser.html) for a Docker Compose
example and troubleshooting.

In code, pass a `BrowserConfig` instead:

```python
from catholic_bible import USCCB
from catholic_bible.challenge import BrowserConfig

async with USCCB(BrowserConfig(cdp_url="http://127.0.0.1:9222")) as usccb:
    ...
```

## API Usage

### Fetch a single chapter

```python
import asyncio
from catholic_bible import USCCB, models

async def main() -> None:
    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1)
        if chapter:
            print(chapter.title)          # "Genesis, Chapter 1"
            print(chapter.url)
            for section in chapter.sections:
                if section.heading:
                    print(section.heading)
                for verse in section.verses:
                    print(verse)          # "1[a] In the beginning..."

asyncio.run(main())
```

### Fetch a single verse

```python
import asyncio
from catholic_bible import USCCB, models

async def main() -> None:
    async with USCCB() as usccb:
        verse = await usccb.get_verse("john", 3, 16)
        if verse:
            print(verse.text)

asyncio.run(main())
```

### Fetch all chapters of a book

```python
import asyncio
from catholic_bible import USCCB, models

async def main() -> None:
    async with USCCB() as usccb:
        chapters = await usccb.get_book("psalms")
    for chapter in chapters:
        print(chapter.title)

asyncio.run(main())
```

### Save chapters to JSON

```python
import asyncio
import json
from pathlib import Path
from catholic_bible import USCCB, models

async def main() -> None:
    async with USCCB() as usccb:
        chapters = await usccb.get_book("genesis")
    out = Path("genesis")
    out.mkdir(exist_ok=True)
    for chapter in chapters:
        (out / f"chapter-{chapter.number:04d}.json").write_text(
            json.dumps(chapter.to_dict(), ensure_ascii=False, indent=2)
        )

asyncio.run(main())
```

### Fetch in Spanish

Pass `language=models.Language.SPANISH` to any method:

```python
import asyncio
from catholic_bible import USCCB, models

async def main() -> None:
    async with USCCB() as usccb:
        chapter = await usccb.get_chapter("genesis", 1, language=models.Language.SPANISH)
        if chapter:
            print(chapter)

asyncio.run(main())
```

### Browse the book catalogue

```python
from catholic_bible import constants

# Attribute access
print(constants.OLD_TESTAMENT_BOOKS.Genesis.num_chapters)   # 50
print(constants.NEW_TESTAMENT_BOOKS.Matthew.name)           # "Matthew"
print(constants.NEW_TESTAMENT_BOOKS.Corinthians1.name)      # "1 Corinthians"

# All 73 books in canonical order
for book in constants.ALL_BOOKS:
    print(book.name, book.num_chapters)

# Lookup by URL name
genesis = constants.BIBLE_BOOKS["genesis"]
print(genesis.short_abbreviation)  # "Gn"
print(genesis.long_abbreviation)   # "Gen"
```

### Book lookup utilities

Books can be looked up by full name, URL name, or abbreviation (case-insensitive):

```python
from catholic_bible.utils import lookup_book, book_url_name

book = lookup_book("Gen")          # long abbreviation
book = lookup_book("Gn")           # short abbreviation
book = lookup_book("genesis")      # URL name (lowercase, no spaces)
book = lookup_book("Genesis")      # full display name
book = lookup_book("Song of Songs")

print(book_url_name(book))         # "songofsongs"
```

## CLI Usage

```sh
# List all 73 books
python -m catholic_bible list-books

# List only Old Testament books
python -m catholic_bible list-books --testament old

# List only New Testament books
python -m catholic_bible list-books --testament new

# Fetch a chapter and print to stdout
python -m catholic_bible get-chapter --book genesis --chapter 1

# Fetch a chapter and save to JSON
python -m catholic_bible get-chapter --book genesis --chapter 1 --save genesis-1.json

# Fetch a single verse
python -m catholic_bible get-verse --book john --chapter 3 --verse 16

# Fetch an entire book (all chapters)
python -m catholic_bible get-book --book psalms

# Save all chapters of a book to a directory
python -m catholic_bible get-book --book genesis --save-dir ./genesis/

# Fetch in Spanish
python -m catholic_bible get-chapter --book genesis --chapter 1 --language SPANISH
python -m catholic_bible get-book --book genesis --language SPANISH --save-dir ./genesis-es/
```

## Key Types

| Type | Description |
|------|-------------|
| `USCCB` | Async client — use as an async context manager |
| `BibleChapter` | A parsed chapter with `book`, `number`, `language`, `url`, `title`, `sections` |
| `BibleSection` | A named section within a chapter (`heading`, `verses`) |
| `BibleVerse` | A single verse (`number`, `text`, `footnote_refs`) |
| `Language` | `Language.ENGLISH` or `Language.SPANISH` |
| `BibleBookInfo` | Book metadata (`name`, `title`, `short_abbreviation`, `long_abbreviation`, `num_chapters`) |

## Documentation

The documentation for `catholic-bible` can be found [here](https://rcolfin.github.io/catholic-bible/)
or in the project's docstrings.

## Development

### Setup Python Environment

```sh
uv install
uvx pre-commit install
```

### Re-lock dependencies

```sh
uv lock
```

### Run code

```sh
uv run python -m catholic_bible
```

### Generating test fixtures

```sh
# Fetch and save a chapter for use as a test fixture
python -m catholic_bible get-chapter --book genesis --chapter 1 --save tests/data/genesis-chapter-1.json
```

### Run tests

```sh
uv run pytest
```
