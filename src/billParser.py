# src/billParser.py
import os
import logging
import pandas as pd
from src import dbManager
from src.parsers import genericPdfParser, hdfcParser, sbiParser, iciciParser, auParser
from src.rewardValidator import validateAndLogRewardSummaries
from src import categorizer, aggregator

logger = logging.getLogger(__name__)

BANK_PARSERS = {
    "HDFC": hdfcParser,
    "SBI": sbiParser,
    "ICICI": iciciParser,
    "AU": auParser,
}


def parseFile(filePath: str):
    """
    Parse a credit card PDF using the appropriate parser.
    Handles both transactions and reward summaries.
    Returns:
        (insertedTxCount, insertedRwCount)
    """
    logging.info(f"Parsing file: {filePath}")

    baseName = os.path.basename(filePath).upper()
    parser_module = None

    for bank, module in BANK_PARSERS.items():
        if bank in baseName:
            parser_module = module
            break

    # --- Parse transactions & rewards ---
    if parser_module:
        logging.info(f"Using {bank} parser")
        transactions, rewardSummaries = parser_module.parse(filePath)
    else:
        logging.warning("No specific parser found, using generic parser")
        transactions = genericPdfParser.parse(filePath)
        rewardSummaries = []

    # --- Ensure cardNumber and clean amounts ---
    if transactions:
        for t in transactions:
            # Fill missing cardNumber with parser-specific fallback
            if not t.get("cardNumber"):
                t["cardNumber"] = f"{baseName.split('_')[0]}-UNKNOWN"
            # Clean amount
            try:
                t["amount"] = float(str(t.get("amount", 0)).replace(",", "").split()[0])
            except Exception as e:
                logger.warning(f"Invalid amount in transaction {t}: {e}")
                t["amount"] = 0.0
        transactions = categorizer.categorizeTransactions(transactions)
        logger.info("Transactions categorized.")

    # --- Insert transactions ---
    txCount = 0
    if transactions:
        txCount = dbManager.insertTransactions(transactions)
        os.makedirs("data/parsed", exist_ok=True)
        txPath = "data/parsed/transactions.csv"
        pd.DataFrame(transactions).to_csv(txPath, index=False)
        logging.info(f"Inserted {txCount} transactions into DB.")
        logging.info(f"Exported parsed transactions to {txPath}")
    else:
        logger.warning("No transactions found.")

    # --- Insert reward summaries ---
    rwCount = 0
    if rewardSummaries:
        warnings = validateAndLogRewardSummaries(rewardSummaries, overwrite=True)
        if warnings:
            logger.warning(f"{len(warnings)} reward summary issue(s) found. See logs/rewardValidationWarnings.csv")
        rwCount = dbManager.insertRewardSummary(rewardSummaries)

        rwPath = "data/parsed/rewardSummaries.csv"
        pd.DataFrame(rewardSummaries).to_csv(rwPath, index=False)
        logger.info(f"Inserted {rwCount} reward summaries into DB.")
        logger.info(f"Exported reward summaries to {rwPath}")
    else:
        logger.warning("No reward summaries found.")

    # --- Load transactions from DB for aggregation ---
    df = aggregator.loadTransactions(fromDb=True)

    # --- Load reward summaries if available ---
    rewardDf = None
    rewardFile = "data/parsed/rewardSummaries.csv"
    if os.path.exists(rewardFile):
        rewardDf = pd.read_csv(rewardFile)
        for col in ["openingBalance", "closingBalance"]:
            if col in rewardDf.columns:
                rewardDf[col] = (
                    rewardDf[col].astype(str).str.replace(",", "").str.strip().astype(float)
                )

    # --- Aggregation ---
    monthlyAgg = aggregator.aggregateByPeriod(df, period="M")
    quarterlyAgg = aggregator.aggregateByPeriod(df, period="Q")
    billSummary = aggregator.aggregateBillSummary(df, rewardDf)

    # --- Export reports ---
    aggregator.exportReport(monthlyAgg, "monthly_aggregation")
    aggregator.exportReport(quarterlyAgg, "quarterly_aggregation")
    aggregator.exportReport(billSummary, "bill_summary")

    return txCount, rwCount
