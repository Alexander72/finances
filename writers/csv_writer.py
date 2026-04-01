import csv
from pathlib import Path

from models import Transaction

HEADER = ["datetime", "person", "name", "tags", "amount", "origin", "description"]


class CsvWriter:
    """Writes all processed Transactions to a single output file."""

    def __init__(self, folder: str | Path) -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def write(self, transactions: list[Transaction]) -> Path:
        output_path = self.folder / "transactions.csv"
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            for transaction in transactions:
                writer.writerow(transaction.to_row())
        return output_path
