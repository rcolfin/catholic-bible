from __future__ import annotations

import importlib.metadata

from catholic_bible import constants, models
from catholic_bible.constants import BibleBookInfo
from catholic_bible.usccb import USCCB

# set the version number within the package using importlib
try:
    __version__: str | None = importlib.metadata.version("catholic-bible")
except importlib.metadata.PackageNotFoundError:
    # package is not installed
    __version__ = None


__all__ = ["BibleBookInfo", "USCCB", "__version__", "constants", "models"]  # noqa: RUF022
