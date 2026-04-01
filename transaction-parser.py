from config import INPUT_FOLDER, OUTPUT_FOLDER, TAG_RULES, DATE_RULES
from pipeline import Pipeline
from processors import (
    DateParserProcessor,
    NameTagProcessor,
    DateTagProcessor,
)
from readers import CsvReader
from writers import CsvWriter

pipeline = Pipeline(
    DateParserProcessor(),
    NameTagProcessor(TAG_RULES),
    DateTagProcessor(DATE_RULES),
)

reader = CsvReader(INPUT_FOLDER)
writer = CsvWriter(OUTPUT_FOLDER)

for source_file, transactions in reader.read():
    processed = [pipeline.process(t) for t in transactions]
    output_path = writer.write(source_file, processed)
    print(f"{source_file.name} → {output_path.name} ({len(processed)} rows)")
