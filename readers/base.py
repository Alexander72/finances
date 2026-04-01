from abc import ABC, abstractmethod
from pathlib import Path

from models import Transaction


class BankReader(ABC):
    """Reads a source file and returns a list of Transactions."""

    @abstractmethod
    def can_handle(self, path: Path) -> bool: ...

    @abstractmethod
    def read(self, path: Path) -> list[Transaction]: ...
