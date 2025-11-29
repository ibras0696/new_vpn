from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Настраивает базовое логирование.

    :param level: уровень логирования (DEBUG/INFO/WARNING/ERROR).
    :return: None.
    """

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
