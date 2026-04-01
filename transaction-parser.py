from pathlib import Path
from datetime import datetime

from config import INPUT_FOLDER, OUTPUT_FOLDER, NAME_TAG_RULES, DATE_RANGE_TAG_RULES
from converters import XlsToCsvConverter
from pipeline import Pipeline
from processors import NameTagProcessor, DateTagProcessor
from readers import IngReader, AbnAmroReader, ReaderRegistry
from writers import CsvWriter

# --- converters ---
converters = [XlsToCsvConverter()]

# --- pipeline ---
pipeline = Pipeline(
    NameTagProcessor(NAME_TAG_RULES),
    DateTagProcessor(DATE_RANGE_TAG_RULES),
)

# --- readers ---
reader_registry = ReaderRegistry([IngReader(), AbnAmroReader()])

# --- writer ---
writer = CsvWriter(OUTPUT_FOLDER)

input_folder = Path(INPUT_FOLDER)

# Phase 1: convert non-CSV formats
for path in sorted(input_folder.iterdir()):
    for converter in converters:
        if converter.can_handle(path):
            out = converter.convert(path)
            print(f"Converted: {path.name} → {out.name}")

# Phase 2: parse CSVs
all_transactions = []
for path in sorted(input_folder.glob("*.csv")):
    reader = reader_registry.find(path)
    if reader is None:
        print(f"Skipped (no reader matched): {path.name}")
        continue
    transactions = reader.read(path)
    processed = [pipeline.process(t) for t in transactions]
    all_transactions.extend(processed)
    print(f"{path.name}: {len(processed)} rows")

all_transactions.sort(key=lambda t: t.datetime or datetime.min)
output_path = writer.write(all_transactions)
print(f"→ {output_path.name} ({len(all_transactions)} rows total)")
