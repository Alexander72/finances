import csv
import re
from pathlib import Path

import xlrd

from .base import FileConverter

_ABNAMRO_PATTERN = re.compile(r"ABN.?AMRO", re.IGNORECASE)


def _cell_to_str(cell) -> str:
    """Convert an xlrd cell to a clean string.

    Integer-valued floats (dates, account numbers) are written without decimal.
    Non-integer floats (amounts, balances) are written as-is.
    """
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        v = cell.value
        return str(int(v)) if v == int(v) else str(v)
    return str(cell.value)


class XlsToCsvConverter(FileConverter):
    """Converts an ABNAMRO .xls export to .csv in the same directory."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".xls" and bool(
            _ABNAMRO_PATTERN.search(path.name)
        )

    def convert(self, path: Path) -> Path:
        wb = xlrd.open_workbook(str(path))
        ws = wb.sheet_by_index(0)
        out_path = path.with_suffix(".csv")
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for i in range(ws.nrows):
                writer.writerow([_cell_to_str(ws.cell(i, j)) for j in range(ws.ncols)])
        return out_path
