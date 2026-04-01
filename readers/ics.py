import csv
import logging
import re
from datetime import datetime
from pathlib import Path

from models import Transaction
from .base import BankReader

logger = logging.getLogger(__name__)


def _parse_dutch_amount(value: str) -> float | None:
    """Parse Dutch-formatted amount: '1.235,41' → 1235.41"""
    try:
        return float(value.replace(".", "").replace(",", "."))
    except ValueError:
        return None


class IcsReader(BankReader):
    """Reads ICS CSV files (converted from PDF) and returns Transactions."""

    def can_handle(self, path: Path) -> bool:
        return "ICS" in path.stem and path.suffix.lower() == ".csv"

    def read(self, path: Path) -> list[Transaction]:
        transactions = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                transactions.append(self._build(row, path))
        return transactions

    @staticmethod
    def _build(row: dict[str, str], path: Path) -> Transaction:
        # --- datetime ---
        date_raw = row.get("transaction_date", "")
        try:
            dt: datetime | None = datetime.strptime(date_raw, "%Y-%m-%d")
        except ValueError:
            if date_raw:
                logger.warning(
                    "%s: could not parse transaction_date '%s'", path.name, date_raw
                )
            dt = None

        # --- amount ---
        amount_raw = row.get("amount_eur", "")
        amount = _parse_dutch_amount(amount_raw)
        if amount is None and amount_raw:
            logger.warning(
                "%s: could not parse amount_eur '%s' on %s",
                path.name,
                amount_raw,
                date_raw,
            )

        if "direction" not in row:
            logger.warning(
                "%s: missing 'direction' column on %s — sign not applied",
                path.name,
                date_raw,
            )
        elif amount is not None and row["direction"] == "Af":
            amount = -amount

        # --- name: raw description as-is ---
        name = row.get("description", "")
        if not name:
            logger.warning("%s: empty description on %s", path.name, date_raw)

        # --- description: append foreign currency info if present ---
        fx_amount = row.get("amount_foreign", "")
        currency = row.get("currency", "")
        exchange_rate = row.get("exchange_rate", "")
        if fx_amount and currency:
            fx_info = f"{fx_amount} {currency}"
            if exchange_rate:
                fx_info += f" @ {exchange_rate}"
            description = f"{name} ({fx_info})"
        else:
            description = name

        return Transaction(
            datetime=dt,
            name=name,
            amount=amount,
            description=description,
            origin="ics",
            source_data=row,
        )
