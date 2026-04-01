from pathlib import Path
from datetime import datetime

from config import INPUT_FOLDER, OUTPUT_FOLDER, NAME_TAG_RULES, DATE_RANGE_TAG_RULES
from converters import XlsToCsvConverter, IcsPdfConverter
from pipeline import Pipeline
from processors import NameTagProcessor, DateTagProcessor, PersonTagProcessor
from readers import IngReader, AbnAmroReader, IcsReader, RevolutReader, ReaderRegistry
from writers import CsvWriter

# --- converters ---
converters = [XlsToCsvConverter(), IcsPdfConverter()]

# --- shared processors (applied to all persons) ---
shared_processors = [
    NameTagProcessor(NAME_TAG_RULES),
    DateTagProcessor(DATE_RANGE_TAG_RULES),
]

# --- readers ---
reader_registry = ReaderRegistry(
    [IngReader(), AbnAmroReader(), IcsReader(), RevolutReader()]
)

# --- writer ---
writer = CsvWriter(OUTPUT_FOLDER)

input_folder = Path(INPUT_FOLDER)
person_dirs = sorted(p for p in input_folder.iterdir() if p.is_dir())

if not person_dirs:
    raise SystemExit(
        f"No person subdirectories found in {input_folder}. "
        "Create one folder per person, e.g. data/input/alexander/"
    )

all_transactions = []

for person_dir in person_dirs:
    person = person_dir.name

    # Phase 1: convert non-CSV formats for this person
    for path in sorted(person_dir.iterdir()):
        for converter in converters:
            if converter.can_handle(path):
                out = converter.convert(path)
                print(f"[{person}] Converted: {path.name} → {out.name}")

    # Phase 2: parse CSVs for this person
    pipeline = Pipeline(*shared_processors, PersonTagProcessor(person))
    for path in sorted(person_dir.glob("*.csv")):
        reader = reader_registry.find(path)
        if reader is None:
            print(f"[{person}] Skipped (no reader matched): {path.name}")
            continue
        transactions = reader.read(path)
        processed = [pipeline.process(t) for t in transactions]
        all_transactions.extend(processed)
        print(f"[{person}] {path.name}: {len(processed)} rows")

all_transactions.sort(key=lambda t: t.datetime or datetime.min)
output_path = writer.write(all_transactions)
print(f"→ {output_path.name} ({len(all_transactions)} rows total)")
