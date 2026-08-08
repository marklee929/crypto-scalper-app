from __future__ import annotations

from typing import Optional

import logging


class Notifier:
    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger

    def notify(self, message: str) -> None:
        if self._logger:
            self._logger.info(message)
            return
        print(message)
