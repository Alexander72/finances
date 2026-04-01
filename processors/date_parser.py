import re
from datetime import datetime

from models import Transaction
from pipeline import TransactionProcessor

# Matches "Datum/Tijd: DD-MM-YYYY HH:MM:SS" — online banking / wire transfers
_PATTERN_DATUM_TIJD = re.compile(
    r"Datum/Tijd:\s*(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2}:\d{2})"
)

# Matches "DD-MM-YYYY HH:MM" anywhere in the memo — card terminals (Pasvolgnr),
# ATMs (Geldautomaat), and iDEAL/Wero (Kenmerk)
_PATTERN_DT_MINUTE = re.compile(r"(\d{2}-\d{2}-\d{4})\s+(\d{2}:\d{2})(?!:\d{2})")


class DateParserProcessor(TransactionProcessor):
    """
    Resolves transaction.dt from the memo field using a three-step strategy:

    1. Datum/Tijd: DD-MM-YYYY HH:MM:SS  (Online bankieren, Overschrijving)
    2. DD-MM-YYYY HH:MM                 (Betaalautomaat, Geldautomaat, iDEAL, Wero)
    3. Fallback: booking_date (col 0)   (Incasso, Diversen, Verzamelbetaling, …)
       → datetime at 00:00:00 to signal no time available
    """

    def process(self, transaction: Transaction) -> Transaction:
        transaction.dt = (
            self._try_datum_tijd(transaction.memo)
            or self._try_dt_minute(transaction.memo)
            or self._from_booking_date(transaction.booking_date)
        )
        return transaction

    @staticmethod
    def _try_datum_tijd(memo: str) -> datetime | None:
        m = _PATTERN_DATUM_TIJD.search(memo)
        if not m:
            return None
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d-%m-%Y %H:%M:%S")

    @staticmethod
    def _try_dt_minute(memo: str) -> datetime | None:
        m = _PATTERN_DT_MINUTE.search(memo)
        if not m:
            return None
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d-%m-%Y %H:%M")

    @staticmethod
    def _from_booking_date(booking_date: str) -> datetime | None:
        try:
            return datetime.strptime(booking_date, "%Y%m%d")
        except ValueError:
            return None
