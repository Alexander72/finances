import csv
from collections import defaultdict
from pathlib import Path

from config import OUTPUT_FOLDER

TRANSACTIONS_FILE = Path(OUTPUT_FOLDER) / "transactions.csv"
REPORT_FILE = Path(OUTPUT_FOLDER) / "report.csv"


def main() -> None:
    totals: dict[tuple[str, str], float] = defaultdict(float)

    with open(TRANSACTIONS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person = row["person"].strip()
            tags_raw = row["tags"].strip()
            amount = float(row["amount"])
            if tags_raw:
                for tag in tags_raw.split(";"):
                    tag = tag.strip()
                    if tag:
                        totals[(person, tag)] += amount
            else:
                totals[(person, "(untagged)")] += amount

    # Sort by person alphabetically, then by total ascending (biggest expenses first)
    sorted_totals = sorted(totals.items(), key=lambda x: (x[0][0], x[1]))

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["person", "tag", "total"])
        for (person, tag), total in sorted_totals:
            writer.writerow([person, tag, f"{total:.2f}"])

    print(f"Report written to {REPORT_FILE} ({len(sorted_totals)} rows)")


if __name__ == "__main__":
    main()
