import csv
import re
from datetime import datetime
from pathlib import Path

from models import Transaction
from .base import BankReader

_ABNAMRO_PATTERN = re.compile(r"ABN.?AMRO", re.IGNORECASE)

# Old format: "... Naam: Nationale-Nederlanden  Machtiging: ..."
_NAAM = re.compile(r"Naam:\s*(.+?)(?:\s{2,}|$)")
# New ISO 20022 format: ".../NAME/Nationale-N.../"
_NAME_SLASH = re.compile(r"/NAME/([^/]+)")
# Card / ATM payments: "BEA, Betaalpas   Merchant Name,PAS512 ..."
_BEA_GEA = re.compile(r"^(?:BEA|GEA),\s*\w+\s+(.+?),PAS", re.IGNORECASE)


def _extract_name(description: str) -> str:
    """Extract payee name from ABNAMRO description field.

    Priority:
    1. Naam: <name>          (old SEPA format)
    2. /NAME/<name>/         (new ISO 20022 format)
    3. BEA/GEA card payment  (merchant name before ,PAS)
    4. First whitespace-collapsed segment (fallback)
    """
    m = _NAAM.search(description)
    if m:
        return m.group(1).strip()

    m = _NAME_SLASH.search(description)
    if m:
        return m.group(1).strip()

    m = _BEA_GEA.search(description)
    if m:
        return m.group(1).strip()

    parts = re.split(r"\s{2,}", description.strip())
    return parts[0].strip() if parts else description


class AbnAmroReader(BankReader):
    """Reads ABNAMRO bank CSV exports (converted from XLS)."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".csv" and bool(
            _ABNAMRO_PATTERN.search(path.name)
        )

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
        date_str = source_data.get("transactiondate", "")
        try:
            dt: datetime | None = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            dt = None

        try:
            amount: float | None = float(source_data.get("amount", ""))
        except ValueError:
            amount = None

        description = source_data.get("description", "")

        return Transaction(
            datetime=dt,
            name=_extract_name(description),
            amount=amount,
            description=description,
            origin="abnamro",
            source_data=source_data,
        )
