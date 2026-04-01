import csv
import re
from datetime import datetime
from pathlib import Path

from models import Transaction
from .base import BankReader

# Matches "Datum/Tijd: DD-MM-YYYY HH:MM:SS" — online banking / wire transfers
_PATTERN_DATUM_TIJD = re.compile(
    r"Datum/Tijd:\s*(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})"
)

# Matches "DD-MM-YYYY HH:MM" anywhere in the memo — card terminals, ATMs, iDEAL, Wero
# Negative lookahead prevents double-matching pattern 1 (which has seconds)
_PATTERN_DT_MINUTE = re.compile(r"(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2})(?!:\d{2})")


def _resolve_datetime(memo: str, booking_date: str) -> datetime | None:
    """Three-step datetime resolution from ING memo field.

    1. Datum/Tijd: DD-MM-YYYY HH:MM:SS  (Online bankieren, Overschrijving)
    2. DD-MM-YYYY HH:MM                 (Betaalautomaat, Geldautomaat, iDEAL, Wero)
    3. Fallback: booking_date YYYYMMDD  → date at 00:00:00
    """
    m = _PATTERN_DATUM_TIJD.search(memo)
    if m:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d-%m-%Y %H:%M:%S")

    m = _PATTERN_DT_MINUTE.search(memo)
    if m:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d-%m-%Y %H:%M")

    try:
        return datetime.strptime(booking_date, "%Y%m%d")
    except ValueError:
        return None


class IngReader(BankReader):
    """Reads ING bank CSV exports."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".csv" and "ing" in path.name.lower()

    def read(self, path: Path) -> list[Transaction]:
        transactions = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                return transactions
            for row in reader:
                if not row:
                    continue
                source_data = dict(zip(header, row))
                transactions.append(self._build(source_data))
        return transactions

    @staticmethod
    def _build(source_data: dict[str, str]) -> Transaction:
        booking_date = source_data.get("Datum", "")
        memo = source_data.get("Mededelingen", "")

        raw_amount = source_data.get("Bedrag (EUR)", "")
        direction = source_data.get("Af Bij", "")
        try:
            amount: float | None = float(raw_amount.replace(",", "."))
            if direction == "Af":
                amount = -amount
        except ValueError:
            amount = None

        return Transaction(
            datetime=_resolve_datetime(memo, booking_date),
            name=source_data.get("Naam / Omschrijving", ""),
            amount=amount,
            description=memo,
            origin="ing",
            source_data=source_data,
        )
