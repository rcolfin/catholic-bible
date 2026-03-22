from __future__ import annotations

from enum import Enum, EnumMeta, unique
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast

if TYPE_CHECKING:
    from collections.abc import Iterable

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


class BibleVerse(NamedTuple):
    """A single numbered verse from a Bible chapter."""

    number: int
    """The verse number within the chapter."""
    text: str
    """The verse text content."""
    footnote_refs: list[str]
    """Footnote reference letters found in this verse (e.g. ['a', 'b'])."""

    def __repr__(self) -> str:
        return f"{self.number}: {self.text[:_REPR_MAX_LEN]}{'...' if len(self.text) > _REPR_MAX_LEN else ''}"

    def __str__(self) -> str:
        refs = "".join(f"[{r}]" for r in self.footnote_refs)
        return f"{self.number}{refs} {self.text}"

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation."""
        r: dict[str, Any] = {"number": self.number, "text": self.text}
        if self.footnote_refs:
            r["footnote_refs"] = list(self.footnote_refs)
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
