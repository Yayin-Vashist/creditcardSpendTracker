# src/aggregator.py
import pandas as pd
import sqlite3
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DB_PATH = "data\\db.sqlite"
REPORT_DIR = "data\\reports"
os.makedirs(REPORT_DIR, exist_ok=True)


def loadTransactions(fromDb: bool = True, filePath: Optional[str] = None, dbPath: str = DB_PATH) -> pd.DataFrame:
    """
    Load transactions from DB or CSV.
    Cleans 'amount', parses 'date', standardizes transactionType.
    """
    if fromDb:
        conn = sqlite3.connect(dbPath)
        df = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        logger.info(f"[LOAD] Loaded {len(df)} transactions from DB")
    else:
        df = pd.read_csv(filePath)
        logger.info(f"[LOAD] Loaded {len(df)} transactions from CSV")

    if df.empty:
        logger.warning("[LOAD] No transactions found!")

    # --- Amount cleaning ---
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(",", "").str.strip(), errors="coerce")
        logger.debug(f"[LOAD] Amounts after numeric conversion:\n{df[['amount']].head()}")
        df["amount"] = df["amount"].fillna(0.0)

    # --- Date parsing ---
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
        null_dates = df["date"].isna().sum()
        if null_dates:
            logger.warning(f"[LOAD] {null_dates} transactions have invalid/missing dates and will be dropped")
        df = df.dropna(subset=["date"])
        logger.debug(f"[LOAD] Transactions after date parsing: {len(df)} rows")

    # --- Standardize transactionType ---
    if "transactionType" in df.columns:
        df["transactionType"] = df["transactionType"].str.upper()
    else:
        df["transactionType"] = "UNKNOWN"

    # --- Card info ---
    df["cardNumber"] = df.get("cardNumber", "UNKNOWN").fillna("UNKNOWN").astype(str).str.strip()
    df["cardHolderName"] = df.get("cardHolderName", "UNKNOWN").fillna("UNKNOWN").astype(str).str.strip()

    # --- Quick per-bank/card summary ---
    for bank in df["sourceBank"].unique():
        subset = df[df["sourceBank"] == bank]
        logger.info(f"[LOAD] {bank} -> {len(subset)} transactions, total amount: {subset['amount'].sum()}")

    return df


def aggregateBillSummary(df: pd.DataFrame, rewardDf: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Aggregate monthly totals per card per holder with proper debit/credit sums.
    """
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["debitAmount"] = df["amount"].where(df["transactionType"] == "DEBIT", 0.0)
    df["creditAmount"] = df["amount"].where(df["transactionType"] == "CREDIT", 0.0)

    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)

    summary = df.groupby(["month", "cardNumber", "cardHolderName"], as_index=False).agg(
        totalDebit=("debitAmount", "sum"),
        totalCredit=("creditAmount", "sum"),
        totalTx=("id", "count")
    )

    if rewardDf is not None and not rewardDf.empty:
        rewardDf = rewardDf.copy()
        for col in ["openingBalance", "closingBalance"]:
            if col in rewardDf.columns:
                rewardDf[col] = pd.to_numeric(rewardDf[col].astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0.0)
        rewardDf["cardNumber"] = rewardDf.get("cardNumber", "UNKNOWN").fillna("UNKNOWN").astype(str).str.strip()
        rewardDf["month"] = pd.to_datetime(rewardDf["statementDate"], errors="coerce").dt.to_period("M")
        logger.debug(f"[AGG] Reward summaries sample:\n{rewardDf.head()}")
        summary = summary.merge(
            rewardDf[["month", "cardNumber", "openingBalance", "closingBalance"]],
            on=["month", "cardNumber"],
            how="left"
        )

    logger.info(f"[AGG] Final summary contains {len(summary)} rows")
    logger.debug(f"[AGG] Summary sample:\n{summary.head()}")
    return summary


def aggregateByPeriod(df: pd.DataFrame, period: str = "M") -> pd.DataFrame:
    """
    Aggregate transactions by period + card + cardHolderName + category/subCategory + transactionType
    Also performs per-period sanity check for totals.
    """
    df = df.copy()
    df["period"] = df["date"].dt.to_period(period)
    df["category"] = df.get("category", "").fillna("Uncategorized").replace("", "Uncategorized")
    df["subCategory"] = df.get("subCategory", "").fillna("Uncategorized").replace("", "Uncategorized")

    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)

    agg = df.groupby(
        ["period", "cardNumber", "cardHolderName", "category", "subCategory", "transactionType"],
        as_index=False
    ).agg(
        totalAmount=("amount", "sum"),
        transactionCount=("id", "count")
    )

    for p in df["period"].unique():
        raw = df[df["period"] == p]
        agg_total = agg[agg["period"] == p].groupby("transactionType")["totalAmount"].sum()
        raw_total = raw.groupby("transactionType")["amount"].sum()
        diff = (agg_total - raw_total).abs()
        if not (diff < 1e-6).all():
            logger.warning(f"[AGG] Aggregation mismatch for period {p}!\nAgg:\n{agg_total}\nRaw:\n{raw_total}")
        else:
            logger.info(f"[AGG] Aggregation and raw totals match for period {p} ✅")
        # Show SBI-specific debug
        sbi_count = len(raw[raw["sourceBank"]=="SBI"])
        logger.info(f"[AGG] Period {p} -> SBI transactions count: {sbi_count}")

    logger.debug(f"[AGG] Aggregated by period ({period}) sample:\n{agg.head()}")
    return agg


def exportReport(df: pd.DataFrame, filename: str, reportDir: str = REPORT_DIR):
    os.makedirs(reportDir, exist_ok=True)
    csvPath = os.path.join(reportDir, f"{filename}.csv")
    excelPath = os.path.join(reportDir, f"{filename}.xlsx")
    df.to_csv(csvPath, index=False)
    df.to_excel(excelPath, index=False, engine="openpyxl")
    logger.info(f"[EXPORT] Exported report: {csvPath} and {excelPath}")