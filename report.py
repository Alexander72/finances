import logging

from reporting import (
    TRANSACTIONS_FILE,
    load_transactions,
    write_all_monthly_reports,
    write_all_annual_reports,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    if not TRANSACTIONS_FILE.exists():
        logger.error(
            "%s not found — run transaction-parser.py first", TRANSACTIONS_FILE
        )
        raise SystemExit(1)

    logger.info("Loading transactions from %s", TRANSACTIONS_FILE)
    df = load_transactions()
    logger.info("Loaded %d transactions", len(df))

    logger.info("Generating monthly reports…")
    monthly_paths = write_all_monthly_reports(df)
    logger.info("Written %d monthly report file(s)", len(monthly_paths))

    logger.info("Generating annual reports…")
    annual_paths = write_all_annual_reports(df)
    logger.info("Written %d annual report file(s)", len(annual_paths))

    total = len(monthly_paths) + len(annual_paths)
    print(f"Done — {total} file(s) written.")


if __name__ == "__main__":
    main()
