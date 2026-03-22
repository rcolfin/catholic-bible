from __future__ import annotations

from typing import Final, NamedTuple


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


class _OldTestamentBooks(NamedTuple):
    """The 46 books of the Catholic Old Testament, accessible by attribute."""

    Genesis: BibleBookInfo
    Exodus: BibleBookInfo
    Leviticus: BibleBookInfo
    Numbers: BibleBookInfo
    Deuteronomy: BibleBookInfo
    Joshua: BibleBookInfo
    Judges: BibleBookInfo
    Ruth: BibleBookInfo
    Samuel1: BibleBookInfo
    Samuel2: BibleBookInfo
    Kings1: BibleBookInfo
    Kings2: BibleBookInfo
    Chronicles1: BibleBookInfo
    Chronicles2: BibleBookInfo
    Ezra: BibleBookInfo
    Nehemiah: BibleBookInfo
    Tobit: BibleBookInfo
    Judith: BibleBookInfo
    Esther: BibleBookInfo
    Maccabees1: BibleBookInfo
    Maccabees2: BibleBookInfo
    Job: BibleBookInfo
    Psalms: BibleBookInfo
    Proverbs: BibleBookInfo
    Ecclesiastes: BibleBookInfo
    SongOfSongs: BibleBookInfo
    Wisdom: BibleBookInfo
    Sirach: BibleBookInfo
    Isaiah: BibleBookInfo
    Jeremiah: BibleBookInfo
    Lamentations: BibleBookInfo
    Baruch: BibleBookInfo
    Ezekiel: BibleBookInfo
    Daniel: BibleBookInfo
    Hosea: BibleBookInfo
    Joel: BibleBookInfo
    Amos: BibleBookInfo
    Obadiah: BibleBookInfo
    Jonah: BibleBookInfo
    Micah: BibleBookInfo
    Nahum: BibleBookInfo
    Habakkuk: BibleBookInfo
    Zephaniah: BibleBookInfo
    Haggai: BibleBookInfo
    Zechariah: BibleBookInfo
    Malachi: BibleBookInfo


class _NewTestamentBooks(NamedTuple):
    """The 27 books of the Catholic New Testament, accessible by attribute."""

    Matthew: BibleBookInfo
    Mark: BibleBookInfo
    Luke: BibleBookInfo
    John: BibleBookInfo
    Acts: BibleBookInfo
    Romans: BibleBookInfo
    Corinthians1: BibleBookInfo
    Corinthians2: BibleBookInfo
    Galatians: BibleBookInfo
    Ephesians: BibleBookInfo
    Philippians: BibleBookInfo
    Colossians: BibleBookInfo
    Thessalonians1: BibleBookInfo
    Thessalonians2: BibleBookInfo
    Timothy1: BibleBookInfo
    Timothy2: BibleBookInfo
    Titus: BibleBookInfo
    Philemon: BibleBookInfo
    Hebrews: BibleBookInfo
    James: BibleBookInfo
    Peter1: BibleBookInfo
    Peter2: BibleBookInfo
    John1: BibleBookInfo
    John2: BibleBookInfo
    John3: BibleBookInfo
    Jude: BibleBookInfo
    Revelation: BibleBookInfo


BIBLE_BASE_URL: Final[str] = "https://bible.usccb.org"
BIBLE_CHAPTER_URL_FMT: Final[str] = "{BASE}/{PREFIX}bible/{BOOK}/{CHAPTER}"

OLD_TESTAMENT_BOOKS: Final[_OldTestamentBooks] = _OldTestamentBooks(
    Genesis=BibleBookInfo("Genesis", "Book of Genesis", "Gn", "Gen", 50),
    Exodus=BibleBookInfo("Exodus", "Book of Exodus", "Ex", "Exod", 40),
    Leviticus=BibleBookInfo("Leviticus", "Book of Leviticus", "Lv", "Lev", 27),
    Numbers=BibleBookInfo("Numbers", "Book of Numbers", "Nm", "Num", 36),
    Deuteronomy=BibleBookInfo("Deuteronomy", "Book of Deuteronomy", "Dt", "Deut", 34),
    Joshua=BibleBookInfo("Joshua", "Book of Joshua", "Jos", "Josh", 24),
    Judges=BibleBookInfo("Judges", "Book of Judges", "Jgs", "Judg", 21),
    Ruth=BibleBookInfo("Ruth", "Book of Ruth", "Ru", "Ruth", 4),
    Samuel1=BibleBookInfo("1 Samuel", "First Book of Samuel", "1Sm", "1Sam", 31),
    Samuel2=BibleBookInfo("2 Samuel", "Second Book of Samuel", "2Sm", "2Sam", 24),
    Kings1=BibleBookInfo("1 Kings", "First Book of Kings", "1Kgs", "1Kgs", 22),
    Kings2=BibleBookInfo("2 Kings", "Second Book of Kings", "2Kgs", "2Kgs", 25),
    Chronicles1=BibleBookInfo("1 Chronicles", "First Book of Chronicles", "1Chr", "1Chr", 29),
    Chronicles2=BibleBookInfo("2 Chronicles", "Second Book of Chronicles", "2Chr", "2Chr", 36),
    Ezra=BibleBookInfo("Ezra", "Book of Ezra", "Ezr", "Ezra", 10),
    Nehemiah=BibleBookInfo("Nehemiah", "Book of Nehemiah", "Ne", "Neh", 13),
    Tobit=BibleBookInfo("Tobit", "Book of Tobit", "Tb", "Tob", 14),
    Judith=BibleBookInfo("Judith", "Book of Judith", "Jdt", "Jdt", 16),
    Esther=BibleBookInfo("Esther", "Book of Esther", "Es", "Est", 16),
    Maccabees1=BibleBookInfo("1 Maccabees", "First Book of Maccabees", "1Mc", "1Mac", 16),
    Maccabees2=BibleBookInfo("2 Maccabees", "Second Book of Maccabees", "2Mc", "2Mac", 15),
    Job=BibleBookInfo("Job", "Book of Job", "Jb", "Job", 42),
    Psalms=BibleBookInfo("Psalms", "Book of Psalms", "Ps", "Psalms", 150),
    Proverbs=BibleBookInfo("Proverbs", "Book of Proverbs", "Pr", "Prv", 31),
    Ecclesiastes=BibleBookInfo("Ecclesiastes", "Book of Ecclesiastes", "Ec", "Eccl", 12),
    SongOfSongs=BibleBookInfo("Song of Songs", "Song of Songs", "Sg", "Song", 8),
    Wisdom=BibleBookInfo("Wisdom", "Book of Wisdom", "Ws", "Wis", 19),
    Sirach=BibleBookInfo("Sirach", "Book of Sirach", "Si", "Sir", 51),
    Isaiah=BibleBookInfo("Isaiah", "Book of the Prophet Isaiah", "Is", "Isa", 66),
    Jeremiah=BibleBookInfo("Jeremiah", "Book of the Prophet Jeremiah", "Jr", "Jer", 52),
    Lamentations=BibleBookInfo("Lamentations", "Book of Lamentations", "Lm", "Lam", 5),
    Baruch=BibleBookInfo("Baruch", "Book of Baruch", "Ba", "Bar", 6),
    Ezekiel=BibleBookInfo("Ezekiel", "Book of the Prophet Ezekiel", "Ez", "Ezek", 48),
    Daniel=BibleBookInfo("Daniel", "Book of the Prophet Daniel", "Dn", "Dan", 14),
    Hosea=BibleBookInfo("Hosea", "Book of the Prophet Hosea", "Ho", "Hos", 14),
    Joel=BibleBookInfo("Joel", "Book of the Prophet Joel", "Jl", "Joel", 4),
    Amos=BibleBookInfo("Amos", "Book of the Prophet Amos", "Am", "Amos", 9),
    Obadiah=BibleBookInfo("Obadiah", "Book of the Prophet Obadiah", "Ob", "Obad", 1),
    Jonah=BibleBookInfo("Jonah", "Book of the Prophet Jonah", "Jon", "Jonah", 4),
    Micah=BibleBookInfo("Micah", "Book of the Prophet Micah", "Mi", "Mic", 7),
    Nahum=BibleBookInfo("Nahum", "Book of the Prophet Nahum", "Na", "Nah", 3),
    Habakkuk=BibleBookInfo("Habakkuk", "Book of the Prophet Habakkuk", "Hb", "Hab", 3),
    Zephaniah=BibleBookInfo("Zephaniah", "Book of the Prophet Zephaniah", "Zp", "Zep", 3),
    Haggai=BibleBookInfo("Haggai", "Book of the Prophet Haggai", "Hg", "Hag", 2),
    Zechariah=BibleBookInfo("Zechariah", "Book of the Prophet Zechariah", "Zc", "Zec", 14),
    Malachi=BibleBookInfo("Malachi", "Book of the Prophet Malachi", "Ml", "Mal", 3),
)

NEW_TESTAMENT_BOOKS: Final[_NewTestamentBooks] = _NewTestamentBooks(
    Matthew=BibleBookInfo("Matthew", "holy Gospel according to Matthew", "Mt", "Matt", 28),
    Mark=BibleBookInfo("Mark", "holy Gospel according to Mark", "Mk", "Mark", 16),
    Luke=BibleBookInfo("Luke", "holy Gospel according to Luke", "Lk", "Luke", 24),
    John=BibleBookInfo("John", "holy Gospel according to John", "Jn", "John", 21),
    Acts=BibleBookInfo("Acts", "Acts of the Apostles", "Ac", "Acts", 28),
    Romans=BibleBookInfo("Romans", "Letter of Saint Paul to the Romans", "Rm", "Rom", 16),
    Corinthians1=BibleBookInfo("1 Corinthians", "First Letter of Saint Paul to the Corinthians", "1C", "1Cor", 16),
    Corinthians2=BibleBookInfo("2 Corinthians", "Second Letter of Saint Paul to the Corinthians", "2C", "2Cor", 13),
    Galatians=BibleBookInfo("Galatians", "Letter of Saint Paul to the Galatians", "Ga", "Gal", 6),
    Ephesians=BibleBookInfo("Ephesians", "Letter of Saint Paul to the Ephesians", "Ep", "Eph", 6),
    Philippians=BibleBookInfo("Philippians", "Letter of Saint Paul to the Philippians", "Ph", "Phil", 4),
    Colossians=BibleBookInfo("Colossians", "Letter of Saint Paul to the Colossians", "Cl", "Col", 4),
    Thessalonians1=BibleBookInfo(
        "1 Thessalonians", "First Letter of Saint Paul to the Thessalonians", "1Th", "1Thes", 5
    ),
    Thessalonians2=BibleBookInfo(
        "2 Thessalonians", "Second Letter of Saint Paul to the Thessalonians", "2Th", "2Thes", 3
    ),
    Timothy1=BibleBookInfo("1 Timothy", "First Letter of Saint Paul to Timothy", "1Tm", "1Tim", 6),
    Timothy2=BibleBookInfo("2 Timothy", "Second Letter of Saint Paul to Timothy", "2Tm", "2Tim", 4),
    Titus=BibleBookInfo("Titus", "Letter of Saint Paul to Titus", "Ti", "Tit", 3),
    Philemon=BibleBookInfo("Philemon", "Letter of Saint Paul to Philemon", "Phlm", "Philem", 1),
    Hebrews=BibleBookInfo("Hebrews", "Letter to the Hebrews", "He", "Heb", 13),
    James=BibleBookInfo("James", "Letter of Saint James", "Jas", "James", 5),
    Peter1=BibleBookInfo("1 Peter", "First Letter of Saint Peter", "1Pt", "1Pet", 5),
    Peter2=BibleBookInfo("2 Peter", "Second Letter of Saint Peter", "2Pt", "2Pet", 3),
    John1=BibleBookInfo("1 John", "First Letter of Saint John", "1Jn", "1John", 5),
    John2=BibleBookInfo("2 John", "Second Letter of Saint John", "2Jn", "2John", 1),
    John3=BibleBookInfo("3 John", "Third Letter of Saint John", "3Jn", "3John", 1),
    Jude=BibleBookInfo("Jude", "Letter of Saint Jude", "Jude", "Jude", 1),
    Revelation=BibleBookInfo("Revelation", "Book of Revelation", "Rv", "Rev", 22),
)

ALL_BOOKS: Final[list[BibleBookInfo]] = [*OLD_TESTAMENT_BOOKS, *NEW_TESTAMENT_BOOKS]
"""All 73 books of the Catholic Bible in canonical order."""

BIBLE_BOOKS: Final[dict[str, BibleBookInfo]] = {book.name.lower().replace(" ", ""): book for book in ALL_BOOKS}
"""Maps URL name (e.g. 'genesis', '1corinthians', 'songofsongs') to BibleBookInfo."""
