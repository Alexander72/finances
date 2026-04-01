import csv
import logging
import re
from datetime import datetime
from pathlib import Path

from models import Transaction
from .base import BankReader

logger = logging.getLogger(__name__)

_ABNAMRO_PATTERN = re.compile(r"ABN.?AMRO", re.IGNORECASE)

# Old format: "... Naam: Nationale-Nederlanden  Machtiging: ..."
_NAAM = re.compile(r"Naam:\s*(.+?)(?:\s{2,}|$)")
# New ISO 20022 format: ".../NAME/Nationale-N.../"
_NAME_SLASH = re.compile(r"/NAME/([^/]+)")
# Card / ATM payments: "BEA, Betaalpas   Merchant Name,PAS512 ..."
_BEA_GEA = re.compile(r"^(?:BEA|GEA),\s*\w+\s+(.+?),PAS", re.IGNORECASE)
# "Pay   Merchant Name" — contactless/debit card prefix with trailing spaces
_PAY_PREFIX = re.compile(r"^Pay\s{2,}", re.IGNORECASE)


def _extract_name(description: str) -> str:
    """Extract payee name from ABNAMRO description field.

    Priority:
    1. Naam: <name>          (old SEPA format)
    2. /NAME/<name>/         (new ISO 20022 format)
    3. BEA/GEA card payment  (merchant name before ,PAS)
    4. First whitespace-collapsed segment (fallback)

    After extraction, a leading "Pay<spaces>" prefix (Apple Pay / contactless)
    is stripped so the actual merchant name is returned.
    """
    m = _NAAM.search(description)
    if m:
        name = m.group(1).strip()
    elif m := _NAME_SLASH.search(description):
        name = m.group(1).strip()
    elif m := _BEA_GEA.search(description):
        name = m.group(1).strip()
    else:
        parts = re.split(r"\s{2,}", description.strip())
        name = parts[0].strip() if parts else description

    return _PAY_PREFIX.sub("", name).strip()


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
            if not header:
                logger.warning("Empty or missing header in %s — skipping", path)
                return transactions
            for row in reader:
                if not row:
                    continue
                source_data = dict(zip(header, row))
                transactions.append(self._build(source_data, path))
        return transactions

    @staticmethod
    def _build(source_data: dict[str, str], path: Path) -> Transaction:
        date_str = source_data.get("transactiondate", "")
        try:
            dt: datetime | None = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            if date_str:
                logger.warning("%s: could not parse date '%s'", path.name, date_str)
            dt = None

        try:
            amount: float | None = float(source_data.get("amount", ""))
        except ValueError:
            logger.warning(
                "%s: could not parse amount '%s' on %s",
                path.name,
                source_data.get("amount", ""),
                date_str,
            )
            amount = None

        description = source_data.get("description", "")
        if not description:
            logger.warning("%s: missing description on %s", path.name, date_str)

        return Transaction(
            datetime=dt,
            name=_extract_name(description),
            amount=amount,
            description=description,
            origin="abnamro",
            source_data=source_data,
        )
