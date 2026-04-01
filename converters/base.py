from abc import ABC, abstractmethod
from pathlib import Path


class FileConverter(ABC):
    """Converts a source file to another format, returning the output path."""

    @abstractmethod
    def can_handle(self, path: Path) -> bool: ...

    @abstractmethod
    def convert(self, path: Path) -> Path: ...
