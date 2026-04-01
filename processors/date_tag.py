import logging
from datetime import datetime

from models import Transaction
from pipeline import TransactionProcessor

logger = logging.getLogger(__name__)


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
    """Adds tags based on date/datetime ranges; skips transactions already tagged 'recurrent'.

    Each rule is a tuple of (start, end, tags) or (start, end, tags, persons).
    If persons is provided, the rule only applies to transactions from those persons.
    """

    def __init__(self, rules: list[tuple]) -> None:
        # Pre-parse rule boundaries once at construction time; skip malformed rules
        self.rules: list[tuple[datetime, datetime, list[str], list[str] | None]] = []
        for i, rule in enumerate(rules):
            try:
                self.rules.append(
                    (
                        _parse_boundary(rule[0], is_end=False),
                        _parse_boundary(rule[1], is_end=True),
                        rule[2],
                        rule[3] if len(rule) >= 4 else None,
                    )
                )
            except (ValueError, IndexError) as e:
                logger.error(
                    "Skipping malformed DATE_RANGE_TAG_RULES entry #%d %s: %s",
                    i,
                    rule,
                    e,
                )

    def process(self, transaction: Transaction) -> Transaction:
        if (
            "recurrent" in transaction.tags
            or "transfers" in transaction.tags
            or transaction.datetime is None
        ):
            return transaction
        for start, end, tags, persons in self.rules:
            if persons is not None and transaction.person not in persons:
                continue
            if start <= transaction.datetime <= end:
                transaction.tags.update(tags)
        return transaction
