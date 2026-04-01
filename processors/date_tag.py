from datetime import datetime

from models import Transaction
from pipeline import TransactionProcessor


def _parse_boundary(value: str, is_end: bool) -> datetime:
    """Parse a rule boundary as datetime.

    Accepts either:
      - "YYYY-MM-DD"           → date-only; expands to 00:00:00 (start) or 23:59:59 (end)
      - "YYYY-MM-DD HH:MM:SS"  → full datetime, used as-is
    """
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.replace(hour=23, minute=59, second=59) if is_end else dt


class DateTagProcessor(TransactionProcessor):
    """Adds tags based on date/datetime ranges; skips transactions already tagged 'fixed'."""

    def __init__(self, rules: list[tuple[str, str, list[str]]]) -> None:
        # Pre-parse rule boundaries once at construction time
        self.rules: list[tuple[datetime, datetime, list[str]]] = [
            (
                _parse_boundary(start, is_end=False),
                _parse_boundary(end, is_end=True),
                tags,
            )
            for start, end, tags in rules
        ]

    def process(self, transaction: Transaction) -> Transaction:
        if "fixed" in transaction.tags or "transfers" in transaction.tags or transaction.datetime is None:
            return transaction
        for start, end, tags in self.rules:
            if start <= transaction.datetime <= end:
                transaction.tags.update(tags)
        return transaction
