from pathlib import Path

from config import INPUT_FOLDER, OUTPUT_FOLDER, TAG_RULES, DATE_RULES
from converters import XlsToCsvConverter
from pipeline import Pipeline
from processors import NameTagProcessor, DateTagProcessor
from readers import IngReader, AbnAmroReader, ReaderRegistry
from writers import CsvWriter

# --- converters ---
converters = [XlsToCsvConverter()]

# --- pipeline ---
pipeline = Pipeline(
    NameTagProcessor(TAG_RULES),
    DateTagProcessor(DATE_RULES),
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
for path in sorted(input_folder.glob("*.csv")):
    reader = reader_registry.find(path)
    if reader is None:
        print(f"Skipped (no reader matched): {path.name}")
        continue
    transactions = reader.read(path)
    processed = [pipeline.process(t) for t in transactions]
    output_path = writer.write(path, processed)
    print(f"{path.name} → {output_path.name} ({len(processed)} rows)")
