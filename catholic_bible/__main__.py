from __future__ import annotations

import logging

from catholic_bible.commands import cli

logger = logging.getLogger(__name__)


def main() -> None:
    cli(_anyio_backend="asyncio")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)-12s: %(levelname)-8s\t%(message)s",
    )

    main()
