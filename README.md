# finances

Personal finance transaction parser supporting ING and ABNAMRO bank exports.

Reads raw files from `data/input/`, enriches each transaction with tags and a resolved datetime, and writes cleaned CSVs to `data/output/`.

## Setup

```bash
git clone <repo>
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config/rules_private.example.py config/rules_private.py
# edit config/rules_private.py — add your TAG_RULES and DATE_RULES
# drop ING *.csv and/or ABNAMRO *.xls files into data/input/
```

## Usage

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python transaction-parser.py
```

ABNAMRO `.xls` files are automatically converted to `.csv` before parsing. One output file is produced per input file: `data/output/<name>_PARSED.csv`.

## Supported formats

| Bank | File format | Notes |
|---|---|---|
| ING | `.csv` | Filename must contain `ING`; datetime extracted from memo field |
| ABNAMRO | `.xls` | Filename must contain `ABNAMRO`; auto-converted to CSV; no time info |

## Output columns

| Column | Description |
|---|---|
| `datetime` | `YYYY-MM-DD HH:MM:SS` when time is known; `YYYY-MM-DD` when only a date is available |
| `name` | Payee / merchant name |
| `tags` | Semicolon-separated computed tags |
| `amount` | Signed float — negative for debits |
| `description` | Full memo / description field from source |

## Tagging rules

Rules live in `config/rules_private.py` (not committed — contains personal data).

**Name rules** — tag by merchant name substring:
```python
NAME_TAG_RULES: list[tuple[list[str], list[str]]] = [
    (["Netflix", "Spotify"], ["subscriptions", "fixed"]),
    (["Albert Heijn", "Jumbo"], ["groceries"]),
]
```

The special tag `fixed` prevents date-range rules from also matching the transaction.

**Date-range rules** — tag by transaction date or datetime:
```python
DATE_RANGE_TAG_RULES: list[tuple[str, str, list[str]]] = [
    ("2025-07-01", "2025-07-14", ["vacation", "trip to Italy"]),
    ("2025-12-24 18:00:00", "2025-12-24 23:59:59", ["christmas dinner"]),
]
```

Boundaries accept `YYYY-MM-DD` (date-only expands to `00:00:00` / `23:59:59`) or `YYYY-MM-DD HH:MM:SS`.

## Project structure

```
transaction-parser.py        entry point (convert phase → parse phase)
requirements.txt             Python dependencies (xlrd)
config/
  rules.py                   folder paths; re-exports from rules_private
  rules_private.py           personal tagging rules (gitignored)
  rules_private.example.py   template — copy this to rules_private.py
models/
  transaction.py             bank-agnostic Transaction dataclass
pipeline/
  __init__.py                TransactionProcessor ABC + Pipeline
processors/
  name_tag.py                applies TAG_RULES
  date_tag.py                applies DATE_RULES
converters/
  base.py                    abstract FileConverter
  xls_to_csv.py              XlsToCsvConverter: ABNAMRO .xls → .csv
readers/
  base.py                    abstract BankReader
  registry.py                ReaderRegistry: selects reader by filename
  ing.py                     ING CSV reader + datetime extraction
  abnamro.py                 ABNAMRO CSV reader + name extraction
writers/
  csv_writer.py              writes output CSVs
data/
  input/                     drop export files here (gitignored)
  output/                    generated files written here (gitignored)
```
