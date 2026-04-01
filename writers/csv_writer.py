import csv
from pathlib import Path

from models import Transaction

HEADER = [
    "datetime",
    "name",
    "tags",
    "amount",
    "account",
    "counter_account",
    "code",
    "direction",
    "transaction_type",
    "memo",
    "balance",
]


class CsvWriter:
    """Writes processed Transactions to the output folder, one file per source."""

    def __init__(self, folder: str | Path) -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def write(self, source: Path, transactions: list[Transaction]) -> Path:
        output_path = self.folder / f"{source.stem}_PARSED{source.suffix}"
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            for transaction in transactions:
                writer.writerow(transaction.to_row())
        return output_path
