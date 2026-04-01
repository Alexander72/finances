from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Transaction:
    datetime: datetime | None  # resolved transaction datetime
    name: str  # payee name
    amount: float | None  # signed float; negative = debit
    description: str  # full memo / description text
    origin: str  # "ing" | "abnamro" | "ics" | "revolut"
    person: str = ""  # subfolder name, e.g. "alexander"
    tags: set[str] = field(default_factory=set)
    source_data: dict[str, str] = field(default_factory=dict)

    def to_row(self) -> list[str]:
        dt = self.datetime
        if dt is None:
            date_str = ""
        elif dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            date_str = dt.strftime("%Y-%m-%d")
        else:
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        amount_str = f"{self.amount:.2f}" if self.amount is not None else ""
        return [
            date_str,
            self.person,
            self.name,
            ";".join(sorted(self.tags)),
            amount_str,
            self.origin,
            self.description,
        ]
