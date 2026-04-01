import csv
from datetime import datetime
from pathlib import Path

from models import Transaction
from .base import BankReader

_CANCELLED_STATUS = "ONGEDAAN GEMAAKT"


class RevolutReader(BankReader):
    """Reads Revolut CSV exports."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".csv" and path.name.upper().startswith(
            "REVOLUT_"
        )

    def read(self, path: Path) -> list[Transaction]:
        transactions = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Status", "").strip() == _CANCELLED_STATUS:
                    continue
                transactions.append(self._build(row))
        return transactions

    @staticmethod
    def _build(source_data: dict[str, str]) -> Transaction:
        raw_dt = source_data.get("Startdatum", "").strip()
        try:
            dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = None

        raw_amount = source_data.get("Bedrag", "").strip()
        try:
            amount: float | None = float(raw_amount)
        except ValueError:
            amount = None

        name = source_data.get("Beschrijving", "").strip()

        return Transaction(
            datetime=dt,
            name=name,
            amount=amount,
            description=name,
            origin="revolut",
            source_data=source_data,
        )
