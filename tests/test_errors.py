"""Tests for custom error exceptions."""

from catholic_bible.errors import InvalidBookError, InvalidChapterError


class TestInvalidBookError:
    def test_error_message_with_closest_match(self) -> None:
        """InvalidBookError should suggest closest match."""
        error = InvalidBookError("corinthians", "1 Corinthians")
        assert str(error) == "Book 'corinthians' not found. Did you mean: 1 Corinthians?"

    def test_error_message_without_closest_match(self) -> None:
        """InvalidBookError should show 'not found' when no match available."""
        error = InvalidBookError("xyz", None)
        assert str(error) == "Book 'xyz' not found"

    def test_error_attributes(self) -> None:
        """InvalidBookError should store book_name and closest_match."""
        error = InvalidBookError("gen", "Genesis")
        assert error.book_name == "gen"
        assert error.closest_match == "Genesis"


class TestInvalidChapterError:
    def test_error_message_format(self) -> None:
        """InvalidChapterError should show max chapters."""
        error = InvalidChapterError("Genesis", 999, 50)
        assert str(error) == "Genesis has 50 chapters, not 999"

    def test_error_attributes(self) -> None:
        """InvalidChapterError should store all attributes."""
        matthew_chapters = 28
        requested_chapter = 100
        error = InvalidChapterError("Matthew", requested_chapter, matthew_chapters)
        assert error.book_name == "Matthew"
        assert error.chapter == requested_chapter
        assert error.max_chapters == matthew_chapters
