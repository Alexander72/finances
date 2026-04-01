import csv
from collections import defaultdict
from pathlib import Path

from config import OUTPUT_FOLDER

TRANSACTIONS_FILE = Path(OUTPUT_FOLDER) / "transactions.csv"
REPORT_FILE = Path(OUTPUT_FOLDER) / "report.csv"


def main() -> None:
    totals: dict[str, float] = defaultdict(float)

    with open(TRANSACTIONS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tags_raw = row["tags"].strip()
            amount = float(row["amount"])
            if tags_raw:
                for tag in tags_raw.split(";"):
                    tag = tag.strip()
                    if tag:
                        totals[tag] += amount
            else:
                totals["(untagged)"] += amount

    sorted_totals = sorted(totals.items(), key=lambda x: x[1])

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tag", "total"])
        for tag, total in sorted_totals:
            writer.writerow([tag, f"{total:.2f}"])

    print(f"Report written to {REPORT_FILE} ({len(sorted_totals)} tags)")


if __name__ == "__main__":
    main()
