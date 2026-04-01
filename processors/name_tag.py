from models import Transaction
from pipeline import TransactionProcessor


class NameTagProcessor(TransactionProcessor):
    """Adds tags based on substrings found in the transaction name."""

    def __init__(self, rules: list[tuple[list[str], list[str]]]) -> None:
        self.rules = rules

    def process(self, transaction: Transaction) -> Transaction:
        name_upper = transaction.name.upper()
        for substrings, tags in self.rules:
            if any(s.upper() in name_upper for s in substrings):
                transaction.tags.update(tags)
        return transaction
