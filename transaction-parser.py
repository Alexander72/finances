from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

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
                try:
                    out = converter.convert(path)
                    print(f"[{person}] Converted: {path.name} → {out.name}")
                except Exception as e:
                    logger.error("Failed to convert %s: %s", path, e)

    # Phase 2: parse CSVs for this person
    pipeline = Pipeline(PersonTagProcessor(person), *shared_processors)
    for path in sorted(person_dir.glob("*.csv")):
        reader = reader_registry.find(path)
        if reader is None:
            logger.warning("No reader matched: %s", path)
            continue
        try:
            transactions = reader.read(path)
        except Exception as e:
            logger.error("Failed to read %s: %s", path, e)
            continue
        processed = []
        for t in transactions:
            try:
                processed.append(pipeline.process(t))
            except Exception as e:
                logger.error(
                    "Failed to process transaction from %s (%s): %s", path, t.name, e
                )
        if any(t.datetime is None for t in processed):
            count = sum(1 for t in processed if t.datetime is None)
            logger.warning(
                "%s: %d transaction(s) have no datetime and will sort to the beginning",
                path.name,
                count,
            )
        all_transactions.extend(processed)
        print(f"[{person}] {path.name}: {len(processed)} rows")

all_transactions.sort(key=lambda t: t.datetime or datetime.min)

try:
    output_path = writer.write(all_transactions)
    print(f"→ {output_path.name} ({len(all_transactions)} rows total)")
except Exception as e:
    logger.error("Failed to write output: %s", e)
    raise SystemExit(1)
