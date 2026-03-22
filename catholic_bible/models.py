from __future__ import annotations

from enum import Enum, EnumMeta, unique
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

from catholic_bible.constants import BibleBookInfo

_REPR_MAX_LEN: Final[int] = 60


class _CaseInsensitiveEnumMeta(EnumMeta):
    def __call__(cls, value: str, *args: Any, **kwargs: Any) -> Enum:  # type: ignore # noqa: PGH003
        try:
            return super().__call__(value, *args, **kwargs)
        except ValueError:
            items = cast("Iterable[Enum]", cls)
            for item in items:
                if item.name.casefold() == value.casefold():
                    return cast("Enum", item)
            raise


@unique
class Language(str, Enum, metaclass=_CaseInsensitiveEnumMeta):
    """Supported Bible languages on bible.usccb.org."""

    ENGLISH = "english"
    SPANISH = "spanish"

    def __repr__(self) -> str:
        return self.name

    @property
    def url_prefix(self) -> str:
        """
        Returns the URL path prefix for this language.

        English has no prefix; Spanish uses 'es/'.

        >>> Language.ENGLISH.url_prefix
        ''
        >>> Language.SPANISH.url_prefix
        'es/'
        """
        if self == Language.SPANISH:
            return "es/"
        return ""


class VerseRef(NamedTuple):
    """A single resolved Bible verse reference from a cross-reference string."""

    book: BibleBookInfo | str
    """The book, either as a resolved BibleBookInfo or raw abbreviation string if unresolved."""
    chapter: int
    """The chapter number (start chapter for chapter ranges)."""
    start_verse: int | None
    """The first verse in the range (or the only verse for a single reference). None for chapter-only refs."""
    end_verse: int | None
    """The last verse in the range. Equal to start_verse for single-verse references. None for chapter-only refs."""
    end_chapter: int | None = None
    """The last chapter for a chapter range (e.g. 45 for 'Gn 37-45'). None for single-chapter refs."""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation. Optional fields are omitted when None.

        >>> from catholic_bible.constants import BibleBookInfo
        >>> VerseRef(BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50, "Gn", "Gén"), 5, 1, 1).to_dict()
        {'book': 'genesis', 'chapter': 5, 'start_verse': 1, 'end_verse': 1}
        >>> VerseRef("UnknownBook", 1, 1, 1).to_dict()
        {'book': 'UnknownBook', 'chapter': 1, 'start_verse': 1, 'end_verse': 1}
        >>> VerseRef("Jos", 3, None, None).to_dict()
        {'book': 'Jos', 'chapter': 3}
        >>> VerseRef("Gn", 37, None, None, 45).to_dict()
        {'book': 'Gn', 'chapter': 37, 'end_chapter': 45}
        """
        from catholic_bible import utils  # noqa: PLC0415

        book_val = utils.book_url_name(self.book) if isinstance(self.book, BibleBookInfo) else self.book
        r: dict[str, Any] = {"book": book_val, "chapter": self.chapter}
        if self.start_verse is not None:
            r["start_verse"] = self.start_verse
        if self.end_verse is not None:
            r["end_verse"] = self.end_verse
        if self.end_chapter is not None:
            r["end_chapter"] = self.end_chapter
        return r


class BibleFootnote(NamedTuple):
    """A single footnote attached to a Bible verse."""

    text: str
    """The footnote text with the leading reference label and verse location stripped."""
    cross_references: list[VerseRef]
    """Structured verse references parsed from the footnote text. Empty for narrative footnotes."""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation. cross_references is omitted when empty.

        >>> BibleFootnote("footnote text", []).to_dict()
        {'text': 'footnote text'}
        """
        r: dict[str, Any] = {"text": self.text}
        if self.cross_references:
            r["cross_references"] = [cr.to_dict() for cr in self.cross_references]
        return r


class BibleVerse(NamedTuple):
    """A single numbered verse from a Bible chapter."""

    number: int
    """The verse number within the chapter."""
    text: str
    """The verse text content."""
    footnotes: list[BibleFootnote]
    """Footnotes found in this verse, each carrying a ref letter and full text."""

    def __repr__(self) -> str:
        return f"{self.number}: {self.text[:_REPR_MAX_LEN]}{'...' if len(self.text) > _REPR_MAX_LEN else ''}"

    def __str__(self) -> str:
        return f"{self.number} {self.text}"

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation."""
        r: dict[str, Any] = {"number": self.number, "text": self.text}
        if self.footnotes:
            r["footnotes"] = [f.to_dict() for f in self.footnotes]
        return r


class BibleSection(NamedTuple):
    """A named section within a Bible chapter (e.g. 'The Story of Creation.')."""

    heading: str | None
    """The section heading, or None if verses have no heading."""
    verses: list[BibleVerse]
    """The verses belonging to this section."""

    def __repr__(self) -> str:
        return f"{self.heading or '(no heading)'} [{len(self.verses)} verses]"

    def __str__(self) -> str:
        lines: list[str] = []
        if self.heading:
            lines.append(self.heading)
        lines.extend(str(v) for v in self.verses)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation."""
        r: dict[str, Any] = {"verses": [v.to_dict() for v in self.verses]}
        if self.heading is not None:
            r["heading"] = self.heading
        return r


class BibleChapter(NamedTuple):
    """A full Bible chapter with its sections and verses."""

    book: str
    """The URL name of the book (e.g. 'genesis', '1corinthians')."""
    number: int
    """The chapter number."""
    language: Language
    """The language of this chapter."""
    url: str
    """The source URL."""
    title: str
    """The page title (e.g. 'Genesis, Chapter 1')."""
    sections: list[BibleSection]
    """The ordered list of sections in this chapter."""

    def __repr__(self) -> str:
        return f"{self.title} ({self.language.name})"

    def __str__(self) -> str:
        lines: list[Any] = [self.title, self.url]
        lines.extend("\n" + str(section) for section in self.sections)
        return "\n".join(map(str, lines))

    @property
    def verses(self) -> list[BibleVerse]:
        """Returns a flat list of all verses across all sections."""
        return [v for section in self.sections for v in section.verses]

    def get_verse(self, number: int) -> BibleVerse | None:
        """
        Returns the verse with the given number, or None if not found.

        Args:
            number (int): The verse number to look up.

        Returns:
            BibleVerse or None.
        """
        for verse in self.verses:
            if verse.number == number:
                return verse
        return None

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation."""
        return {
            "book": self.book,
            "language": self.language.value,
            "number": self.number,
            "sections": [s.to_dict() for s in self.sections],
            "title": self.title,
            "url": self.url,
        }
