from pathlib import Path

from .base import BankReader
from models import Transaction


class ReaderRegistry:
    """Dispatches files to the appropriate BankReader by filename."""

    def __init__(self, readers: list[BankReader]) -> None:
        self.readers = readers

    def find(self, path: Path) -> BankReader | None:
        for reader in self.readers:
            if reader.can_handle(path):
                return reader
        return None
