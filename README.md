# finances

Personal finance transaction parser for ING bank CSV exports.

Reads raw CSVs from `data/input/`, enriches each transaction with tags and a resolved datetime, and writes cleaned CSVs to `data/output/`.

## Setup

```bash
git clone <repo>
cp config/rules_private.example.py config/rules_private.py
# edit config/rules_private.py — add your TAG_RULES and DATE_RULES
# drop ING export *.csv files into data/input/
python3 transaction-parser.py
```

No dependencies beyond the Python standard library.

## Usage

```bash
python3 transaction-parser.py
```

One output file is produced per input file: `data/output/<name>_PARSED.csv`.

## Output columns

| Column | Description |
|---|---|
| `datetime` | Actual transaction datetime from memo field; falls back to booking date |
| `name` | Payee name |
| `tags` | Semicolon-separated computed tags |
| `amount` | Signed float — negative for debits |
| `account` | Own account number |
| `counter_account` | Counter-party account number |
| `code` | ING transaction code |
| `direction` | `Af` (debit) or `Bij` (credit) |
| `transaction_type` | ING mutation type |
| `memo` | Full memo field |
| `balance` | Balance after transaction |

## Tagging rules

Rules live in `config/rules_private.py` (not committed — contains personal data).

**Name rules** — tag by merchant name substring:
```python
TAG_RULES = [
    (["Netflix", "Spotify"], ["subscriptions", "fixed"]),
    (["Albert Heijn", "Jumbo"], ["groceries"]),
]
```

The special tag `fixed` prevents date-range rules from also matching the transaction.

**Date-range rules** — tag by transaction date or datetime:
```python
DATE_RULES = [
    ("2025-07-01", "2025-07-14", ["vacation", "trip to Italy"]),
    ("2025-12-24 18:00:00", "2025-12-24 23:59:59", ["christmas dinner"]),
]
```

Boundaries accept `YYYY-MM-DD` (date-only expands to `00:00:00` / `23:59:59`) or `YYYY-MM-DD HH:MM:SS`.

## Project structure

```
transaction-parser.py        entry point
config/
  rules.py                   folder paths; re-exports from rules_private
  rules_private.py           personal tagging rules (gitignored)
  rules_private.example.py   template — copy this to rules_private.py
models/
  transaction.py             Transaction dataclass
pipeline/
  __init__.py                TransactionProcessor ABC + Pipeline
processors/
  date_parser.py             resolves transaction datetime from memo
  name_tag.py                applies TAG_RULES
  date_tag.py                applies DATE_RULES
readers/
  csv_reader.py              discovers and reads input CSVs
writers/
  csv_writer.py              writes output CSVs
data/
  input/                     drop ING export files here (gitignored)
  output/                    generated files written here (gitignored)
```
