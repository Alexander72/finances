import csv
from collections.abc import Iterator
from pathlib import Path

from models import Transaction


class CsvReader:
    """Discovers and reads all CSV files in a folder, yielding Transactions per file."""

    def __init__(self, folder: str | Path, delimiter: str = ",") -> None:
        self.folder = Path(folder)
        self.delimiter = delimiter

    def read(self) -> Iterator[tuple[Path, list[Transaction]]]:
        for path in sorted(self.folder.glob("*.csv")):
            yield path, self._read_file(path)

    def _read_file(self, path: Path) -> list[Transaction]:
        transactions = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=self.delimiter)
            next(reader, None)  # skip header row
            for row in reader:
                if row:
                    transactions.append(Transaction.from_row(row))
        return transactions
