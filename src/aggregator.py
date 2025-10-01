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


import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def aggregateBillSummary(df: pd.DataFrame, rewardDf: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Aggregate monthly totals per card per holder with proper debit/credit sums.
    Enhanced with per-card logging for better visibility.
    """
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["debitAmount"] = df["amount"].where(df["transactionType"] == "DEBIT", 0.0)
    df["creditAmount"] = df["amount"].where(df["transactionType"] == "CREDIT", 0.0)
    
    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)
    
    # Log data overview before aggregation
    logger.info(f"[AGG-BILL] Processing {len(df)} transactions across {df['month'].nunique()} months")
    logger.info(f"[AGG-BILL] Unique cards found: {df['cardNumber'].nunique()}")
    
    # Show breakdown by card and bank
    for card in df['cardNumber'].unique():
        card_data = df[df['cardNumber'] == card]
        bank = card_data['sourceBank'].iloc[0] if 'sourceBank' in card_data.columns else 'UNKNOWN'
        holder = card_data['cardHolderName'].iloc[0] if not card_data.empty else 'UNKNOWN'
        logger.info(f"[AGG-BILL]   └─ {bank} ({card[:20]}...) - {holder}: {len(card_data)} transactions")
    
    summary = df.groupby(["month", "cardNumber", "cardHolderName"], as_index=False).agg(
        totalDebit=("debitAmount", "sum"),
        totalCredit=("creditAmount", "sum"),
        totalTx=("id", "count")
    )
    
    # Log monthly breakdown per card
    logger.info(f"[AGG-BILL] Monthly summary by card:")
    for _, row in summary.iterrows():
        logger.info(
            f"[AGG-BILL]   {row['month']} | {row['cardHolderName']} | "
            f"Debit: ₹{row['totalDebit']:,.2f} | Credit: ₹{row['totalCredit']:,.2f} | "
            f"Txns: {row['totalTx']}"
        )
    
    if rewardDf is not None and not rewardDf.empty:
        rewardDf = rewardDf.copy()
        for col in ["openingBalance", "closingBalance"]:
            if col in rewardDf.columns:
                rewardDf[col] = pd.to_numeric(
                    rewardDf[col].astype(str).str.replace(",", "").str.strip(), 
                    errors="coerce"
                ).fillna(0.0)
        
        rewardDf["cardNumber"] = rewardDf.get("cardNumber", "UNKNOWN").fillna("UNKNOWN").astype(str).str.strip()
        rewardDf["month"] = pd.to_datetime(rewardDf["statementDate"], errors="coerce").dt.to_period("M")
        
        logger.debug(f"[AGG-BILL] Merging reward data: {len(rewardDf)} reward records")
        logger.debug(f"[AGG-BILL] Reward summaries sample:\n{rewardDf.head()}")
        
        summary = summary.merge(
            rewardDf[["month", "cardNumber", "openingBalance", "closingBalance"]],
            on=["month", "cardNumber"],
            how="left"
        )
        
        # Log which cards got reward data matched
        matched = summary[summary['openingBalance'].notna()]
        if not matched.empty:
            logger.info(f"[AGG-BILL] Reward data matched for {len(matched)} month-card combinations")
    
    logger.info(f"[AGG-BILL] ✅ Final summary contains {len(summary)} rows")
    logger.debug(f"[AGG-BILL] Summary sample:\n{summary.head()}")
    
    return summary


def aggregateByPeriod(df: pd.DataFrame, period: str = "M") -> pd.DataFrame:
    """
    Aggregate transactions by period + card + cardHolderName + category/subCategory + transactionType.
    Enhanced with comprehensive per-card and per-bank logging.
    """
    df = df.copy()
    df["period"] = df["date"].dt.to_period(period)
    df["category"] = df.get("category", "").fillna("Uncategorized").replace("", "Uncategorized")
    df["subCategory"] = df.get("subCategory", "").fillna("Uncategorized").replace("", "Uncategorized")
    
    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)
    
    # Enhanced logging: Show data overview
    logger.info(f"[AGG-PERIOD] Processing {len(df)} transactions")
    logger.info(f"[AGG-PERIOD] Periods: {sorted(df['period'].unique())}")
    logger.info(f"[AGG-PERIOD] Unique cards: {df['cardNumber'].nunique()}")
    
    # Show card-to-bank mapping
    if 'sourceBank' in df.columns:
        card_bank_map = df.groupby(['cardNumber', 'sourceBank']).size().reset_index(name='count')
        logger.info(f"[AGG-PERIOD] Card-to-Bank mapping:")
        for _, row in card_bank_map.iterrows():
            logger.info(f"[AGG-PERIOD]   └─ {row['sourceBank']}: {row['cardNumber'][:25]}... ({row['count']} txns)")
    
    agg = df.groupby(
        ["period", "cardNumber", "cardHolderName", "category", "subCategory", "transactionType"],
        as_index=False
    ).agg(
        totalAmount=("amount", "sum"),
        transactionCount=("id", "count")
    )
    
    # Enhanced per-period validation with card-level details
    for p in sorted(df["period"].unique()):
        logger.info(f"\n[AGG-PERIOD] ═══ Validating Period: {p} ═══")
        raw = df[df["period"] == p]
        
        # Overall totals check
        agg_period = agg[agg["period"] == p]
        agg_total = agg_period.groupby("transactionType")["totalAmount"].sum()
        raw_total = raw.groupby("transactionType")["amount"].sum()
        diff = (agg_total - raw_total).abs()
        
        if not (diff < 1e-6).all():
            logger.warning(f"[AGG-PERIOD] ⚠️  Aggregation mismatch for period {p}!")
            logger.warning(f"[AGG-PERIOD] Aggregated:\n{agg_total}")
            logger.warning(f"[AGG-PERIOD] Raw:\n{raw_total}")
        else:
            logger.info(f"[AGG-PERIOD] ✅ Aggregation matches raw totals")
        
        # Per-bank breakdown
        if 'sourceBank' in raw.columns:
            logger.info(f"[AGG-PERIOD] Breakdown by bank:")
            for bank in sorted(raw['sourceBank'].unique()):
                bank_data = raw[raw['sourceBank'] == bank]
                debit_sum = bank_data[bank_data['transactionType'] == 'DEBIT']['amount'].sum()
                credit_sum = bank_data[bank_data['transactionType'] == 'CREDIT']['amount'].sum()
                logger.info(
                    f"[AGG-PERIOD]   └─ {bank}: {len(bank_data)} txns | "
                    f"Debit: ₹{debit_sum:,.2f} | Credit: ₹{credit_sum:,.2f}"
                )
        
        # Per-card breakdown
        logger.info(f"[AGG-PERIOD] Breakdown by card:")
        for card in sorted(raw['cardNumber'].unique()):
            card_data = raw[raw['cardNumber'] == card]
            holder = card_data['cardHolderName'].iloc[0] if not card_data.empty else 'UNKNOWN'
            bank = card_data['sourceBank'].iloc[0] if 'sourceBank' in card_data.columns else 'UNKNOWN'
            debit_sum = card_data[card_data['transactionType'] == 'DEBIT']['amount'].sum()
            credit_sum = card_data[card_data['transactionType'] == 'CREDIT']['amount'].sum()
            logger.info(
                f"[AGG-PERIOD]   └─ {bank} - {holder} ({card[:25]}...): "
                f"{len(card_data)} txns | Debit: ₹{debit_sum:,.2f} | Credit: ₹{credit_sum:,.2f}"
            )
        
        # Category breakdown for the period
        logger.info(f"[AGG-PERIOD] Top 5 categories by transaction count:")
        top_cats = raw.groupby('category').size().sort_values(ascending=False).head(5)
        for cat, count in top_cats.items():
            logger.info(f"[AGG-PERIOD]   └─ {cat}: {count} txns")
    
    logger.info(f"\n[AGG-PERIOD] ✅ Aggregation complete: {len(agg)} aggregated rows")
    logger.debug(f"[AGG-PERIOD] Aggregated sample:\n{agg.head(10)}")
    
    return agg

def exportReport(df: pd.DataFrame, filename: str, reportDir: str = REPORT_DIR):
    os.makedirs(reportDir, exist_ok=True)
    csvPath = os.path.join(reportDir, f"{filename}.csv")
    excelPath = os.path.join(reportDir, f"{filename}.xlsx")
    df.to_csv(csvPath, index=False)
    df.to_excel(excelPath, index=False, engine="openpyxl")
    logger.info(f"[EXPORT] Exported report: {csvPath} and {excelPath}")