# finances

Personal finance transaction parser supporting ING, ABNAMRO, ICS, and Revolut bank exports.

Reads raw files from `data/input/<person>/`, enriches each transaction with tags and a resolved datetime, and writes cleaned CSVs to `data/output/`.

## Setup

```bash
git clone <repo>
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config/rules_private.example.py config/rules_private.py
cp config/rules_private.example.py config/rules_private.py
# edit config/rules_private.py — add your TAG_RULES and DATE_RULES
# create one subfolder per person under data/input/, e.g.:
#   data/input/alexander/
#   data/input/maria/
# drop each person's bank export files into their subfolder
```

## Usage

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python transaction-parser.py
```

ABNAMRO `.xls` and ICS `.pdf` files are automatically converted to `.csv` before parsing. All transactions from all persons are merged into a single output file: `data/output/transactions.csv`. Each transaction is tagged with the person's subfolder name.

## Reports

```bash
python report.py
```

Reads `data/output/transactions.csv` and writes `data/output/report.csv` — total spend per tag, sorted ascending (biggest expenses first). Transactions with multiple tags are counted in each tag. Untagged transactions appear as `(untagged)`.

## Supported formats

| Bank | File format | Notes |
|---|---|---|
| ING | `.csv` | Filename must contain `ING`; datetime extracted from memo field |
| ABNAMRO | `.xls` | Filename must contain `ABNAMRO`; auto-converted to CSV; no time info |
| ICS | `.pdf` | Filename must contain `ICS`; auto-converted to CSV; no time info |
| Revolut | `.csv` | Filename must start with `REVOLUT_`; full datetime available; cancelled transactions skipped |

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
    (["Netflix", "Spotify"], ["subscriptions", "recurrent"]),
    (["Albert Heijn", "Jumbo"], ["groceries"]),
]
```

The special tag `recurrent` prevents date-range rules from also matching the transaction.

**Date-range rules** — tag by transaction date or datetime. An optional 4th element restricts the rule to specific persons; omit it to apply to everyone:
```python
DATE_RANGE_TAG_RULES: list[tuple] = [
    # applies to everyone
    ("2025-12-24 18:00:00", "2025-12-24 23:59:59", ["christmas dinner"]),
    # applies only to alexander
    ("2025-07-01", "2025-07-14", ["vacation", "trip to Italy"], ["alexander"]),
    # applies to alexander and maria
    ("2025-08-01", "2025-08-15", ["vacation", "trip to Greece"], ["alexander", "maria"]),
]
```

Boundaries accept `YYYY-MM-DD` (date-only expands to `00:00:00` / `23:59:59`) or `YYYY-MM-DD HH:MM:SS`.

## Project structure

```
transaction-parser.py        entry point (convert phase → parse phase)
report.py                    per-tag summary report
requirements.txt             Python dependencies (xlrd, pdfplumber)
config/
  rules.py                   folder paths; re-exports from rules_private
  rules_private.py           personal tagging rules (gitignored)
  rules_private.example.py   template — copy this to rules_private.py
models/
  transaction.py             bank-agnostic Transaction dataclass
pipeline/
  __init__.py                TransactionProcessor ABC + Pipeline
processors/
  name_tag.py                applies NAME_TAG_RULES (by merchant name)
  date_tag.py                applies DATE_RANGE_TAG_RULES (by date range)
  person_tag.py              tags each transaction with the person's name
converters/
  base.py                    abstract FileConverter
  xls_to_csv.py              XlsToCsvConverter: ABNAMRO .xls → .csv
  ics_pdf_to_csv.py          IcsPdfConverter: ICS .pdf → .csv
readers/
  base.py                    abstract BankReader
  registry.py                ReaderRegistry: selects reader by filename
  ing.py                     ING CSV reader + datetime extraction
  abnamro.py                 ABNAMRO CSV reader + name extraction
  ics.py                     ICS CSV reader (converted from PDF)
  revolut.py                 Revolut CSV reader
writers/
  csv_writer.py              writes output CSVs
data/
  input/                     gitignored; one subfolder per person
    alexander/               drop alexander's export files here
    maria/                   drop maria's export files here
  output/                    generated files written here (gitignored)
```
