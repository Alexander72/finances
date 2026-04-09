"""
Reporting module — Data section (steps 1–7).

Computes monthly and annual metrics from transactions.csv as described in
report-requirements.md.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import pandas as pd

from config import OUTPUT_FOLDER

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRANSACTIONS_FILE = Path(OUTPUT_FOLDER) / "transactions.csv"

META_TAGS: frozenset[str] = frozenset({"recurrent", "subscriptions", "transfers"})


# ---------------------------------------------------------------------------
# Step 1 — Load data
# ---------------------------------------------------------------------------


def load_transactions(path: Path = TRANSACTIONS_FILE) -> pd.DataFrame:
    """Read transactions.csv and return a clean DataFrame.

    Columns returned:
        datetime  – pandas Timestamp (NaT where unparseable)
        person    – str
        name      – str
        tags      – frozenset[str]  (empty frozenset when blank)
        amount    – float           (NaN where unparseable)
        origin    – str
        description – str
        month     – str  YYYY-MM   (derived, Step 3)
        year      – str  YYYY      (derived, Step 3)
    """
    df = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
    )

    # --- Step 1: parse datetime ---
    df["datetime"] = pd.to_datetime(df["datetime"], format="mixed", errors="coerce")

    # --- Step 1: parse amount ---
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # --- Step 1: parse tags ---
    def _parse_tags(raw: str) -> frozenset[str]:
        return frozenset(t.strip() for t in raw.split(";") if t.strip())

    df["tags"] = df["tags"].apply(_parse_tags)

    # --- Step 3: derived period columns ---
    df["month"] = df["datetime"].dt.strftime("%Y-%m")
    df["year"] = df["datetime"].dt.strftime("%Y")

    return df


# ---------------------------------------------------------------------------
# Step 2 — Row-classification helpers (vectorised boolean Series)
# ---------------------------------------------------------------------------


def mask_transfer(df: pd.DataFrame) -> pd.Series:
    """True where the row is a transfer (excluded from all metrics)."""
    return df["tags"].apply(lambda t: "transfers" in t)

def mask_salary(df: pd.DataFrame) -> pd.Series:
    """True where the row is a salary (income)."""
    return df["tags"].apply(lambda t: "salary" in t)


def mask_mortgage_extra(df: pd.DataFrame) -> pd.Series:
    """True where the row is a mortgage extra payment."""
    return df["tags"].apply(lambda t: "mortgage-extra-payment" in t)


def mask_income(df: pd.DataFrame) -> pd.Series:
    """True where amount > 0 AND not a transfer."""
    return (df["amount"] > 0) & ~mask_transfer(df)


def mask_spending(df: pd.DataFrame) -> pd.Series:
    """True where amount < 0 AND not a transfer AND not mortgage-extra-payment."""
    return ~mask_salary(df) & ~mask_mortgage_extra(df) & ~mask_transfer(df)


def mask_recurrent(df: pd.DataFrame) -> pd.Series:
    """True where spending row AND 'recurrent' in tags."""
    return mask_spending(df) & df["tags"].apply(lambda t: "recurrent" in t)


# ---------------------------------------------------------------------------
# Step 4 — Tag-grouping helper
# ---------------------------------------------------------------------------


def tag_spendings(
    df_period: pd.DataFrame,
    total_spendings: float,
    n_months: int,
    top_n: int = 10,
    include_avg_monthly: bool = False,
) -> pd.DataFrame:
    """Return a ranked tag-spending table.

    Parameters
    ----------
    df_period:
        Transactions restricted to the reporting period (month or year).
    total_spendings:
        Pre-computed absolute total spendings for the period (used for %).
    n_months:
        Number of distinct calendar months in the period (used for avg_monthly).
    top_n:
        Number of tags to keep (10 for monthly, 20 for annual).
    include_avg_monthly:
        When True, add an ``avg_monthly`` column (used in annual reports).

    Returns
    -------
    summary : pd.DataFrame
        Columns: tag, total, pct[, avg_monthly]
        Sorted descending by total, limited to top_n.
    """
    spending_rows = df_period[mask_spending(df_period)].copy()

    if spending_rows.empty:
        empty = pd.DataFrame(columns=["tag", "total", "pct"])
        if include_avg_monthly:
            empty["avg_monthly"] = pd.Series(dtype=float)
        return empty

    # Explode: one row per (original_index, tag).
    # A transaction with N tags contributes its full amount to each tag.
    records = []
    for _, row in spending_rows.iterrows():
        tags = row["tags"] - META_TAGS  # exclude meta-tags from ranking
        if not tags:
            continue
        for tag in tags:
            records.append({"tag": tag, "amount": row["amount"]})

    if not records:
        empty = pd.DataFrame(columns=["tag", "total", "pct"])
        if include_avg_monthly:
            empty["avg_monthly"] = pd.Series(dtype=float)
        return empty

    exploded = pd.DataFrame(records)

    agg = (
        exploded.groupby("tag")["amount"]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"amount": "total"})
    )
    agg["pct"] = (
        (agg["total"] / total_spendings * 100).round(2) if total_spendings else 0.0
    )

    if include_avg_monthly:
        agg["avg_monthly"] = (agg["total"] / n_months).round(2) if n_months else 0.0

    return agg.sort_values("total", ascending=False).head(top_n).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 5 — compute_monthly_metrics
# ---------------------------------------------------------------------------


def compute_monthly_metrics(df: pd.DataFrame, month: str) -> dict:
    """Compute all Data-section metrics for a single calendar month.

    Parameters
    ----------
    df:
        Full transactions DataFrame produced by load_transactions().
    month:
        Period string in ``YYYY-MM`` format.

    Returns
    -------
    dict with keys:
        month               str
        income              float  — sum of income amounts
        total_spendings     float  — absolute sum of spending amounts
        top10_tags          pd.DataFrame  — tag, total, pct
        fixed_spendings     float  — absolute sum of recurrent spending amounts
        fixed_pct           float  — fixed_spendings / total_spendings * 100
        profit              float  — income − total_spendings (signed: positive = surplus)
        profit_pct          float  — profit / income * 100
        top10_individual    pd.DataFrame  — top 10 spending rows in transactions.csv format
    """
    df_month = df[df["month"] == month].copy()

    n_months = 1  # by definition a monthly report covers exactly one month

    # 1. Income
    income = float(df_month.loc[mask_income(df_month), "amount"].sum())

    # 2. Total spendings
    total_spendings = float(abs(df_month.loc[mask_spending(df_month), "amount"].sum()))

    # 4. Fixed / recurrent spendings
    fixed_spendings = float(abs(df_month.loc[mask_recurrent(df_month), "amount"].sum()))
    fixed_pct = (fixed_spendings / total_spendings * 100) if total_spendings else 0.0

    # 3. Top-10 tag spendings
    top10_tags = tag_spendings(
        df_month,
        total_spendings=total_spendings,
        n_months=n_months,
        top_n=10,
        include_avg_monthly=False,
    )

    # 5. Profit
    profit = income - total_spendings
    profit_pct = (profit / income * 100) if income else 0.0

    # 6. Top-10 biggest individual spendings
    spending_rows = df_month[mask_spending(df_month)].copy()
    top10_individual = (
        spending_rows[
            ["datetime", "person", "name", "tags", "amount", "origin", "description"]
        ]
        .sort_values("amount", ascending=True)
        .head(10)
        .reset_index(drop=True)
    )
    top10_individual["tags"] = top10_individual["tags"].apply(
        lambda t: ";".join(sorted(t))
    )

    return {
        "month": month,
        "income": round(income, 2),
        "total_spendings": round(total_spendings, 2),
        "top10_tags": top10_tags,
        "fixed_spendings": round(fixed_spendings, 2),
        "fixed_pct": round(fixed_pct, 2),
        "profit": round(profit, 2),
        "profit_pct": round(profit_pct, 2),
        "top10_individual": top10_individual,
    }


# ---------------------------------------------------------------------------
# Step 6 — compute_annual_metrics
# ---------------------------------------------------------------------------


def compute_annual_metrics(df: pd.DataFrame, year: str) -> dict:
    """Compute all Data-section metrics for a single calendar year.

    Parameters
    ----------
    df:
        Full transactions DataFrame produced by load_transactions().
    year:
        Period string in ``YYYY`` format.

    Returns
    -------
    dict with keys:
        year                    str
        n_months                int    — distinct calendar months with ≥1 transaction
        income                  float
        avg_monthly_income      float  — income / N
        total_spendings         float
        avg_monthly_spending    float  — total_spendings / N
        mortgage_extra          float  — absolute sum of mortgage-extra-payment rows
        top20_tags              pd.DataFrame  — tag, total, pct, avg_monthly
        recurrent_spendings     float
        recurrent_pct           float
        recurrent_avg_monthly   float  — recurrent_spendings / N
        profit_total            float
        profit_pct              float  — profit_total / income * 100
        profit_avg              float  — profit_total / N
        profit_avg_pct          float  — profit_avg / avg_income * 100
        top20_individual        pd.DataFrame  — datetime, name, tags, amount
    """
    df_year = df[df["year"] == year].copy()

    # N: distinct calendar months that have at least one transaction
    n_months = int(df_year["month"].dropna().nunique())
    if n_months == 0:
        n_months = 1  # guard against division by zero for empty years

    # 1. Income
    income = float(df_year.loc[mask_income(df_year), "amount"].sum())
    avg_monthly_income = round(income / n_months, 2) if n_months else 0.0

    # 2. Total spendings
    total_spendings = float(abs(df_year.loc[mask_spending(df_year), "amount"].sum()))

    # 3. Average monthly spending
    avg_monthly_spending = round(total_spendings / n_months, 2) if n_months else 0.0

    # 4. Mortgage extra payments
    mortgage_mask = df_year["tags"].apply(lambda t: "mortgage-extra-payment" in t)
    mortgage_extra = float(abs(df_year.loc[mortgage_mask, "amount"].sum()))

    # 5. Top-20 tag spendings (with avg_monthly per tag)
    top20_tags = tag_spendings(
        df_year,
        total_spendings=total_spendings,
        n_months=n_months,
        top_n=20,
        include_avg_monthly=True,
    )

    # 6. Total recurrent spendings
    recurrent_spendings = float(
        abs(df_year.loc[mask_recurrent(df_year), "amount"].sum())
    )
    recurrent_pct = (
        (recurrent_spendings / total_spendings * 100) if total_spendings else 0.0
    )
    recurrent_avg_monthly = (
        round(recurrent_spendings / n_months, 2) if n_months else 0.0
    )

    # 7. Profit total
    profit_total = income - total_spendings
    profit_pct = (profit_total / income * 100) if income else 0.0

    # 8. Profit average per month
    profit_avg = round(profit_total / n_months, 2) if n_months else 0.0
    avg_income = income / n_months if n_months else 0.0
    profit_avg_pct = (profit_avg / avg_income * 100) if avg_income else 0.0

    # 9. Top-20 biggest individual spendings by value
    spending_rows = df_year[mask_spending(df_year)].copy()
    top20_individual = (
        spending_rows[["datetime", "name", "tags", "amount"]]
        .sort_values("amount", ascending=True)
        .head(20)
        .reset_index(drop=True)
    )
    # Render tags as semicolon-separated string for readability
    top20_individual = top20_individual.copy()
    top20_individual["tags"] = top20_individual["tags"].apply(
        lambda t: ";".join(sorted(t))
    )

    return {
        "year": year,
        "n_months": n_months,
        "income": round(income, 2),
        "avg_monthly_income": avg_monthly_income,
        "total_spendings": round(total_spendings, 2),
        "avg_monthly_spending": avg_monthly_spending,
        "mortgage_extra": round(mortgage_extra, 2),
        "top20_tags": top20_tags,
        "recurrent_spendings": round(recurrent_spendings, 2),
        "recurrent_pct": round(recurrent_pct, 2),
        "recurrent_avg_monthly": recurrent_avg_monthly,
        "profit_total": round(profit_total, 2),
        "profit_pct": round(profit_pct, 2),
        "profit_avg": profit_avg,
        "profit_avg_pct": round(profit_avg_pct, 2),
        "top20_individual": top20_individual,
    }


# ---------------------------------------------------------------------------
# Step 7 — Write monthly report CSVs
# ---------------------------------------------------------------------------

REPORTS_DIR = Path(OUTPUT_FOLDER) / "reports"

_FMT = "{:.2f}".format  # shorthand for formatting floats


def write_monthly_report(metrics: dict, output_dir: Path = REPORTS_DIR) -> list[Path]:
    """Write one month's metrics to separate CSV files inside a per-month folder.

    Folder / files produced
    -----------------------
    {output_dir}/monthly_{YYYY-MM}/
        summary.csv             — scalar metrics (income, spendings, profit)
        top10_tags.csv          — top-10 tag spendings table
        top10_transactions.csv  — top-10 individual spending transactions
    """
    month = metrics["month"]
    month_dir = output_dir / f"monthly_{month}"
    month_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # --- File 1: summary scalars ---
    summary_path = month_dir / "summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "pct"])
        w.writerow(["income", _FMT(metrics["income"]), ""])
        w.writerow(["total_spendings", _FMT(metrics["total_spendings"]), ""])
        w.writerow(
            [
                "fixed_spendings",
                _FMT(metrics["fixed_spendings"]),
                _FMT(metrics["fixed_pct"]),
            ]
        )
        w.writerow(["profit", _FMT(metrics["profit"]), _FMT(metrics["profit_pct"])])
    logger.info("Wrote %s", summary_path)
    written.append(summary_path)

    # --- File 2: top-10 tag spendings ---
    tags_path = month_dir / "top10_tags.csv"
    with open(tags_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "total_eur", "pct"])
        for _, row in metrics["top10_tags"].iterrows():
            w.writerow([row["tag"], _FMT(row["total"]), _FMT(row["pct"])])
    logger.info("Wrote %s", tags_path)
    written.append(tags_path)

    # --- File 3: top-10 individual transactions ---
    tx_path = month_dir / "top10_transactions.csv"
    metrics["top10_individual"].to_csv(tx_path, index=False)
    logger.info("Wrote %s", tx_path)
    written.append(tx_path)

    return written


def write_all_monthly_reports(
    df: pd.DataFrame, output_dir: Path = REPORTS_DIR
) -> list[Path]:
    """Compute and write report CSVs for every distinct month in *df*."""
    months = sorted(df["month"].dropna().unique())
    paths: list[Path] = []
    for month in months:
        metrics = compute_monthly_metrics(df, month)
        paths.extend(write_monthly_report(metrics, output_dir))
    return paths


# ---------------------------------------------------------------------------
# Step 8 — Write annual report CSVs
# ---------------------------------------------------------------------------

# Order matches monthly summary.csv (value rows + pct as separate metric rows).
_SUMMARY_BY_MONTHS_METRICS: tuple[str, ...] = (
    "income",
    "total_spendings",
    "fixed_spendings",
    "fixed_pct",
    "profit",
    "profit_pct",
)


def write_summary_by_months_csv(
    df: pd.DataFrame, year: str, year_dir: Path
) -> Path | None:
    """Write wide monthly breakdown for *year* (same scalars as monthly summary.csv).

    One row per metric; ``fixed_pct`` and ``profit_pct`` are separate rows. Columns are
    ``metric`` plus one column per calendar month that exists in *df* for that year.
    Returns the path written, or None if there are no months for *year*.
    """
    prefix = f"{year}-"
    months = sorted(
        m for m in df["month"].dropna().unique() if str(m).startswith(prefix)
    )
    path = year_dir / "summary_by_months.csv"
    if not months:
        return None

    by_month: dict[str, tuple[float, float, float, float, float, float]] = {}
    for m in months:
        cm = compute_monthly_metrics(df, m)
        by_month[m] = (
            cm["income"],
            cm["total_spendings"],
            cm["fixed_spendings"],
            cm["fixed_pct"],
            cm["profit"],
            cm["profit_pct"],
        )

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", *months])
        for i, name in enumerate(_SUMMARY_BY_MONTHS_METRICS):
            w.writerow([name, *(_FMT(by_month[m][i]) for m in months)])
    logger.info("Wrote %s", path)
    return path


def write_annual_report(
    df: pd.DataFrame, metrics: dict, output_dir: Path = REPORTS_DIR
) -> list[Path]:
    """Write one year's metrics to separate CSV files inside a per-year folder.

    Folder / files produced
    -----------------------
    {output_dir}/annual_{YYYY}/
        summary.csv             — scalar metrics (income, spendings, profit, mortgage)
        summary_by_months.csv   — monthly summary scalars (wide, from compute_monthly_metrics)
        top20_tags.csv          — top-20 tag spendings table
        top20_transactions.csv  — top-20 biggest individual spending transactions
    """
    year = metrics["year"]
    year_dir = output_dir / f"annual_{year}"
    year_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # --- File 1: summary scalars ---
    summary_path = year_dir / "summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "pct", "avg_monthly"])
        w.writerow(["income", _FMT(metrics["income"]), "", _FMT(metrics["avg_monthly_income"])])
        w.writerow(
            [
                "total_spendings",
                _FMT(metrics["total_spendings"]),
                "",
                _FMT(metrics["avg_monthly_spending"]),
            ]
        )
        w.writerow(["mortgage_extra", _FMT(metrics["mortgage_extra"]), "", ""])
        w.writerow(
            [
                "recurrent_spendings",
                _FMT(metrics["recurrent_spendings"]),
                _FMT(metrics["recurrent_pct"]),
                _FMT(metrics["recurrent_avg_monthly"]),
            ]
        )
        w.writerow(
            [
                "profit_total",
                _FMT(metrics["profit_total"]),
                _FMT(metrics["profit_pct"]),
                _FMT(metrics["profit_avg"]),
            ]
        )
    logger.info("Wrote %s", summary_path)
    written.append(summary_path)

    smb = write_summary_by_months_csv(df, year, year_dir)
    if smb is not None:
        written.append(smb)

    # --- File 2: top-20 tag spendings ---
    tags_path = year_dir / "top20_tags.csv"
    with open(tags_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag", "total_eur", "pct", "avg_monthly"])
        for _, row in metrics["top20_tags"].iterrows():
            w.writerow(
                [
                    row["tag"],
                    _FMT(row["total"]),
                    _FMT(row["pct"]),
                    _FMT(row["avg_monthly"]),
                ]
            )
    logger.info("Wrote %s", tags_path)
    written.append(tags_path)

    # --- File 3: top-20 individual transactions ---
    tx_path = year_dir / "top20_transactions.csv"
    metrics["top20_individual"].to_csv(tx_path, index=False)
    logger.info("Wrote %s", tx_path)
    written.append(tx_path)

    return written


def write_all_annual_reports(
    df: pd.DataFrame, output_dir: Path = REPORTS_DIR
) -> list[Path]:
    """Compute and write report CSVs for every distinct year in *df*."""
    years = sorted(df["year"].dropna().unique())
    paths: list[Path] = []
    for year in years:
        metrics = compute_annual_metrics(df, year)
        paths.extend(write_annual_report(df, metrics, output_dir))
    return paths
