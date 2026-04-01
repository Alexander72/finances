from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Transaction:
    booking_date: str  # raw col 0 (YYYYMMDD) — settlement date, kept for reference
    name: str  # col 1
    amount: float | None  # col 6  Bedrag (EUR); None if unparseable
    memo: str  # col 8  Mededelingen — source of actual datetime
    dt: datetime | None = None  # resolved by DateParserProcessor; None until then
    tags: set[str] = field(default_factory=set)
    extra: list[str] = field(default_factory=list)  # cols 2-5, 7, 9-10

    @classmethod
    def from_row(cls, row: list[str]) -> "Transaction":
        raw_amount = row[6] if len(row) > 6 else ""
        direction = row[5] if len(row) > 5 else ""
        try:
            amount: float | None = float(raw_amount.replace(",", "."))
            if direction == "Af":
                amount = -amount
        except ValueError:
            amount = None  # unparseable value

        return cls(
            booking_date=row[0],
            name=row[1] if len(row) > 1 else "",
            amount=amount,
            memo=row[8] if len(row) > 8 else "",
            # cols 2-5, 7, 9+ go into extra (cols 6 and 8 extracted above)
            extra=(row[2:6] + row[7:8] + row[9:]) if len(row) > 2 else [],
        )

    def to_row(self) -> list[str]:
        if self.dt is None:
            date_str = self.booking_date
        elif self.dt.hour == 0 and self.dt.minute == 0 and self.dt.second == 0:
            date_str = self.dt.strftime("%Y-%m-%d")  # date-only fallback
        else:
            date_str = self.dt.strftime("%Y-%m-%d %H:%M:%S")  # full datetime

        # extra indices (from from_row: cols 2-5, 7, then 9-10):
        #   [0] col 2  Rekening
        #   [1] col 3  Tegenrekening
        #   [2] col 4  Code
        #   [3] col 5  Af Bij
        #   [4] col 7  Mutatiesoort
        #   [5] col 9  Saldo na mutatie
        #   [6] col 10 Tag (original) ← replaced by computed tags

        # Output order: datetime, name, tags, amount, all remaining original cols
        rest = [
            self.extra[0] if len(self.extra) > 0 else "",  # col 2  Rekening
            self.extra[1] if len(self.extra) > 1 else "",  # col 3  Tegenrekening
            self.extra[2] if len(self.extra) > 2 else "",  # col 4  Code
            self.extra[3] if len(self.extra) > 3 else "",  # col 5  Af Bij
            self.extra[4] if len(self.extra) > 4 else "",  # col 7  Mutatiesoort
            self.memo,  # col 8  Mededelingen
            self.extra[5] if len(self.extra) > 5 else "",  # col 9  Saldo na mutatie
        ]
        amount_str = f"{self.amount:.2f}" if self.amount is not None else ""
        return [date_str, self.name, ";".join(sorted(self.tags)), amount_str] + rest
