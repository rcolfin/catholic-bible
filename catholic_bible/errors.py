"""Custom exceptions for CLI error handling."""

from __future__ import annotations


class BibleError(Exception):
    """Base exception for Bible lookup errors."""


class InvalidBookError(BibleError):
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


class InvalidChapterError(BibleError):
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
