from abc import ABC, abstractmethod

from models import Transaction


class TransactionProcessor(ABC):
    @abstractmethod
    def process(self, transaction: Transaction) -> Transaction: ...


class Pipeline:
    def __init__(self, *processors: TransactionProcessor) -> None:
        self.processors = processors

    def process(self, transaction: Transaction) -> Transaction:
        for processor in self.processors:
            transaction = processor.process(transaction)
        return transaction
