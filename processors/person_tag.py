from models import Transaction
from pipeline import TransactionProcessor


class PersonTagProcessor(TransactionProcessor):
    """Sets the person field on every transaction."""

    def __init__(self, person: str) -> None:
        self.person = person

    def process(self, transaction: Transaction) -> Transaction:
        transaction.person = self.person
        return transaction
