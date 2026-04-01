import csv
import logging
import re
from pathlib import Path

import xlrd

from .base import FileConverter

logger = logging.getLogger(__name__)

_ABNAMRO_PATTERN = re.compile(r"ABN.?AMRO", re.IGNORECASE)


def _cell_to_str(cell) -> str:
    """Convert an xlrd cell to a clean string.

    Integer-valued floats (dates, account numbers) are written without decimal.
    Non-integer floats (amounts, balances) are written as-is.
    """
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        v = cell.value
        try:
            if v == int(v):
                return str(int(v))
        except (ValueError, OverflowError):
            logger.warning("Skipping int conversion for non-finite cell value: %s", v)
        return str(v)
    return str(cell.value)


class XlsToCsvConverter(FileConverter):
    """Converts an ABNAMRO .xls export to .csv in the same directory."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".xls" and bool(
            _ABNAMRO_PATTERN.search(path.name)
        )

    def convert(self, path: Path) -> Path:
        try:
            wb = xlrd.open_workbook(str(path))
        except Exception as e:
            logger.error("Could not open XLS file %s: %s", path, e)
            raise

        try:
            ws = wb.sheet_by_index(0)
        except IndexError:
            logger.error("XLS file %s contains no sheets", path)
            raise

        out_path = path.with_suffix(".csv")
        try:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for i in range(ws.nrows):
                    writer.writerow(
                        [_cell_to_str(ws.cell(i, j)) for j in range(ws.ncols)]
                    )
        except OSError as e:
            logger.error("Could not write CSV to %s: %s", out_path, e)
            raise

        return out_path
