import csv
import re
from datetime import date
from pathlib import Path

import pdfplumber

from .base import FileConverter

# Dutch month name mappings
_MONTHS_ABBREV: dict[str, int] = {
    "jan.": 1,
    "feb.": 2,
    "mrt.": 3,
    "apr.": 4,
    "mei.": 5,
    "jun.": 6,
    "jul.": 7,
    "aug.": 8,
    "sep.": 9,
    "okt.": 10,
    "nov.": 11,
    "dec.": 12,
}
_MONTHS_FULL: dict[str, int] = {
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}

# x-coordinate column boundaries (from PDF word analysis)
_COL_TX_DATE = (56, 102)
_COL_BOOKING_DATE = (102, 152)
_COL_DESCRIPTION = (152, 400)
_COL_FX = (400, 478)
_COL_EUR = (478, 533)
_COL_DIRECTION = (533, 580)

# Minimum word height to exclude invisible/garbage text embedded in the PDF
_MIN_WORD_HEIGHT = 4.0

CSV_HEADER = [
    "transaction_date",
    "booking_date",
    "description",
    "amount_foreign",
    "currency",
    "exchange_rate",
    "amount_eur",
    "direction",
]


def _in_col(words: list[dict], x_min: int, x_max: int) -> list[dict]:
    return [w for w in words if x_min <= w["x0"] < x_max]


def _parse_abbrev_date(day: str, month: str) -> tuple[int, int]:
    return int(day), _MONTHS_ABBREV.get(month.lower(), 0)


def _resolve_year(tx_month: int, stmt_month: int, stmt_year: int) -> int:
    """December transactions on a January statement belong to the prior year."""
    return stmt_year - 1 if tx_month > stmt_month else stmt_year


class IcsPdfConverter(FileConverter):
    """Converts ICS credit card PDF statements to intermediate CSV files."""

    def can_handle(self, path: Path) -> bool:
        return "ICS" in path.stem and path.suffix.lower() == ".pdf"

    def convert(self, path: Path) -> Path:
        out_path = path.with_suffix(".csv")
        rows = self._parse_pdf(path)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            writer.writerows(rows)
        return out_path

    def _parse_pdf(self, path: Path) -> list[dict]:
        with pdfplumber.open(path) as pdf:
            all_words: list[dict] = []
            for page in pdf.pages:
                all_words.extend(
                    w for w in page.extract_words() if w["height"] >= _MIN_WORD_HEIGHT
                )

        stmt_month, stmt_year = self._extract_statement_date(all_words)
        lines = self._group_into_lines(all_words)
        return self._extract_transactions(lines, stmt_month, stmt_year)

    @staticmethod
    def _extract_statement_date(words: list[dict]) -> tuple[int, int]:
        """Locate 'DD <full_month> YYYY' in the statement header."""
        texts = [w["text"].lower() for w in words]
        for i, text in enumerate(texts):
            if text in _MONTHS_FULL and i + 1 < len(words):
                year_text = words[i + 1]["text"]
                if re.fullmatch(r"\d{4}", year_text):
                    return _MONTHS_FULL[text], int(year_text)
        raise ValueError("Could not find statement date in PDF")

    @staticmethod
    def _group_into_lines(words: list[dict]) -> list[list[dict]]:
        """Group words into lines by top coordinate (2 px tolerance)."""
        buckets: dict[int, list[dict]] = {}
        for word in words:
            top_key = round(word["top"])
            bucket = next((k for k in buckets if abs(k - top_key) <= 2), None)
            if bucket is None:
                bucket = top_key
                buckets[bucket] = []
            buckets[bucket].append(word)
        return [
            sorted(words, key=lambda w: w["x0"])
            for words in (buckets[k] for k in sorted(buckets))
        ]

    def _extract_transactions(
        self, lines: list[list[dict]], stmt_month: int, stmt_year: int
    ) -> list[dict]:
        rows: list[dict] = []

        for line in lines:
            tx_date_words = _in_col(line, *_COL_TX_DATE)
            booking_words = _in_col(line, *_COL_BOOKING_DATE)
            desc_words = _in_col(line, *_COL_DESCRIPTION)
            fx_words = _in_col(line, *_COL_FX)
            eur_words = _in_col(line, *_COL_EUR)
            dir_words = _in_col(line, *_COL_DIRECTION)

            tx_texts = [w["text"] for w in tx_date_words]
            dir_texts = [w["text"] for w in dir_words]

            # --- Transaction row ---
            if (
                len(tx_texts) == 2
                and re.fullmatch(r"\d{1,2}", tx_texts[0])
                and re.fullmatch(r"[a-z]+\.", tx_texts[1].lower())
                and dir_texts
                and dir_texts[0] in ("Af", "Bij")
            ):
                tx_day, tx_month = _parse_abbrev_date(tx_texts[0], tx_texts[1])
                tx_year = _resolve_year(tx_month, stmt_month, stmt_year)
                tx_date = date(tx_year, tx_month, tx_day).isoformat()

                bk_texts = [w["text"] for w in booking_words]
                if len(bk_texts) == 2:
                    bk_day, bk_month = _parse_abbrev_date(bk_texts[0], bk_texts[1])
                    bk_year = _resolve_year(bk_month, stmt_month, stmt_year)
                    booking_date = date(bk_year, bk_month, bk_day).isoformat()
                else:
                    booking_date = tx_date

                description = " ".join(w["text"] for w in desc_words)

                fx_amount = fx_words[0]["text"] if len(fx_words) >= 1 else ""
                currency = fx_words[1]["text"] if len(fx_words) >= 2 else ""
                eur_amount = " ".join(w["text"] for w in eur_words)

                rows.append(
                    {
                        "transaction_date": tx_date,
                        "booking_date": booking_date,
                        "description": description,
                        "amount_foreign": fx_amount,
                        "currency": currency,
                        "exchange_rate": "",
                        "amount_eur": eur_amount,
                        "direction": dir_texts[0],
                    }
                )

            # --- Wisselkoers (exchange rate) continuation line ---
            elif desc_words and desc_words[0]["text"] == "Wisselkoers" and rows:
                # Format: "Wisselkoers CCY rate" — rate word ends up in desc_col
                rate_words = [w["text"] for w in desc_words]
                # rate_words = ["Wisselkoers", "CCY", "rate_value"]
                rate = rate_words[2] if len(rate_words) >= 3 else ""
                rows[-1]["exchange_rate"] = rate

        return rows
