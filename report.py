import csv
import logging
from collections import defaultdict
from pathlib import Path

from config import OUTPUT_FOLDER

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

TRANSACTIONS_FILE = Path(OUTPUT_FOLDER) / "transactions.csv"


def main() -> None:
    if not TRANSACTIONS_FILE.exists():
        logger.error(
            "%s not found — run transaction-parser.py first", TRANSACTIONS_FILE
        )
        raise SystemExit(1)

    # totals[person][tag] = float
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    skipped = 0

    with open(TRANSACTIONS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and not {"person", "tags", "amount"}.issubset(
            reader.fieldnames
        ):
            logger.error(
                "Unexpected columns in %s: %s", TRANSACTIONS_FILE, reader.fieldnames
            )
            raise SystemExit(1)
        for row in reader:
            try:
                amount = float(row["amount"])
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Skipping row with unparseable amount (%s): %s", e, dict(row)
                )
                skipped += 1
                continue
            person = row.get("person", "").strip()
            tags_raw = row.get("tags", "").strip()
            if tags_raw:
                for tag in tags_raw.split(";"):
                    tag = tag.strip()
                    if tag:
                        totals[person][tag] += amount
            else:
                totals[person]["(untagged)"] += amount

    if skipped:
        logger.warning("Skipped %d row(s) due to unparseable amounts", skipped)

    output_dir = Path(OUTPUT_FOLDER)

    # Per-person reports
    for person, tag_totals in sorted(totals.items()):
        sorted_rows = sorted(tag_totals.items(), key=lambda x: x[1])
        report_file = output_dir / f"report_{person}.csv"
        try:
            with open(report_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["tag", "total"])
                for tag, total in sorted_rows:
                    writer.writerow([tag, f"{total:.2f}"])
        except OSError as e:
            logger.error("Failed to write report to %s: %s", report_file, e)
            raise SystemExit(1)
        print(f"Report written to {report_file} ({len(sorted_rows)} rows)")

    # Aggregated report across all persons
    aggregated: dict[str, float] = defaultdict(float)
    for tag_totals in totals.values():
        for tag, total in tag_totals.items():
            aggregated[tag] += total
    sorted_agg = sorted(aggregated.items(), key=lambda x: x[1])
    agg_file = output_dir / "report_all.csv"
    try:
        with open(agg_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tag", "total"])
            for tag, total in sorted_agg:
                writer.writerow([tag, f"{total:.2f}"])
    except OSError as e:
        logger.error("Failed to write report to %s: %s", agg_file, e)
        raise SystemExit(1)
    print(f"Report written to {agg_file} ({len(sorted_agg)} rows)")


if __name__ == "__main__":
    main()
