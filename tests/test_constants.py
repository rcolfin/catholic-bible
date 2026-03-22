from __future__ import annotations

from catholic_bible import constants


def test_old_testament_attribute_access() -> None:
    assert constants.OLD_TESTAMENT_BOOKS.Genesis.name == "Genesis"
    assert constants.OLD_TESTAMENT_BOOKS.Exodus.name == "Exodus"
    assert constants.OLD_TESTAMENT_BOOKS.Samuel1.name == "1 Samuel"
    assert constants.OLD_TESTAMENT_BOOKS.Samuel2.name == "2 Samuel"
    assert constants.OLD_TESTAMENT_BOOKS.SongOfSongs.name == "Song of Songs"
    assert constants.OLD_TESTAMENT_BOOKS.Malachi.name == "Malachi"


def test_new_testament_attribute_access() -> None:
    assert constants.NEW_TESTAMENT_BOOKS.Matthew.name == "Matthew"
    assert constants.NEW_TESTAMENT_BOOKS.John.name == "John"
    assert constants.NEW_TESTAMENT_BOOKS.Corinthians1.name == "1 Corinthians"
    assert constants.NEW_TESTAMENT_BOOKS.Corinthians2.name == "2 Corinthians"
    assert constants.NEW_TESTAMENT_BOOKS.John1.name == "1 John"
    assert constants.NEW_TESTAMENT_BOOKS.John2.name == "2 John"
    assert constants.NEW_TESTAMENT_BOOKS.John3.name == "3 John"
    assert constants.NEW_TESTAMENT_BOOKS.Revelation.name == "Revelation"


def test_old_testament_chapter_counts() -> None:
    assert constants.OLD_TESTAMENT_BOOKS.Genesis.num_chapters == 50  # noqa: PLR2004
    assert constants.OLD_TESTAMENT_BOOKS.Psalms.num_chapters == 150  # noqa: PLR2004
    assert constants.OLD_TESTAMENT_BOOKS.Obadiah.num_chapters == 1


def test_new_testament_chapter_counts() -> None:
    assert constants.NEW_TESTAMENT_BOOKS.Matthew.num_chapters == 28  # noqa: PLR2004
    assert constants.NEW_TESTAMENT_BOOKS.Revelation.num_chapters == 22  # noqa: PLR2004
    assert constants.NEW_TESTAMENT_BOOKS.Philemon.num_chapters == 1


def test_old_testament_abbreviations() -> None:
    genesis = constants.OLD_TESTAMENT_BOOKS.Genesis
    assert genesis.short_abbreviation == "Gn"
    assert genesis.long_abbreviation == "Gen"


def test_new_testament_abbreviations() -> None:
    matthew = constants.NEW_TESTAMENT_BOOKS.Matthew
    assert matthew.short_abbreviation == "Mt"
    assert matthew.long_abbreviation == "Matt"


def test_all_books_count() -> None:
    assert len(constants.ALL_BOOKS) == 73  # noqa: PLR2004


def test_all_books_canonical_order() -> None:
    assert constants.ALL_BOOKS[0].name == "Genesis"
    assert constants.ALL_BOOKS[46].name == "Matthew"  # first NT book (46 OT books, 0-indexed)
    assert constants.ALL_BOOKS[-1].name == "Revelation"


def test_bible_books_dict_lookup() -> None:
    assert constants.BIBLE_BOOKS["genesis"].name == "Genesis"
    assert constants.BIBLE_BOOKS["1corinthians"].name == "1 Corinthians"
    assert constants.BIBLE_BOOKS["songofsongs"].name == "Song of Songs"
    assert constants.BIBLE_BOOKS["revelation"].name == "Revelation"


def test_bible_books_dict_size() -> None:
    assert len(constants.BIBLE_BOOKS) == 73  # noqa: PLR2004
