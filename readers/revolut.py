import csv
import logging
from datetime import datetime
from pathlib import Path

from models import Transaction
from .base import BankReader

logger = logging.getLogger(__name__)

# Revolut exports in both Dutch and English; map to canonical field names
_COLUMN_MAP = {
    # Dutch locale
    "Startdatum": "started_date",
    "Beschrijving": "description",
    "Bedrag": "amount",
    "Status": "state",
    # English locale
    "Started Date": "started_date",
    "Description": "description",
    "Amount": "amount",
    "State": "state",
}

# Status values that indicate a cancelled/reverted transaction
_CANCELLED_STATES = {"ONGEDAAN GEMAAKT", "REVERTED"}


class RevolutReader(BankReader):
    """Reads Revolut CSV exports (Dutch and English locale)."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".csv" and path.name.upper().startswith(
            "REVOLUT_"
        )

    def read(self, path: Path) -> list[Transaction]:
        transactions = []
        # utf-8-sig strips the UTF-8 BOM that Revolut sometimes includes
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                logger.error("%s: empty or unreadable header", path.name)
                return transactions

            # Build a normalised row accessor: raw_col -> canonical key
            col_lookup: dict[str, str] = {}
            for raw_col in reader.fieldnames:
                canonical = _COLUMN_MAP.get(raw_col.strip())
                if canonical:
                    col_lookup[raw_col.strip()] = canonical

            for row in reader:
                norm = {v: row[k].strip() for k, v in col_lookup.items() if k in row}
                state = norm.get("state", "")
                if state in _CANCELLED_STATES:
                    continue
                # Skip rows where both amount and description are blank
                if not norm.get("amount") and not norm.get("description"):
                    continue
                transactions.append(self._build(norm, row, path))
        return transactions

    @staticmethod
    def _build(
        norm: dict[str, str], source_data: dict[str, str], path: Path
    ) -> Transaction:
        raw_dt = norm.get("started_date", "")
        try:
            dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            if raw_dt:
                logger.warning("%s: could not parse date '%s'", path.name, raw_dt)
            dt = None

        raw_amount = norm.get("amount", "")
        try:
            amount: float | None = float(raw_amount)
        except ValueError:
            if raw_amount:
                logger.warning(
                    "%s: could not parse amount '%s' on %s",
                    path.name,
                    raw_amount,
                    raw_dt,
                )
            amount = None

        name = norm.get("description", "")
        if not name:
            logger.warning("%s: empty description on %s", path.name, raw_dt)

        return Transaction(
            datetime=dt,
            name=name,
            amount=amount,
            description=name,
            origin="revolut",
            source_data=source_data,
        )
