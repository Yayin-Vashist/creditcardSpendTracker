# src/parsers/auParser.py
"""
Parser for AU Credit Card PDF Statements.

Extracts:
- Transactions: date, description, amount, debit/credit, reward points.
- Reward summary: opening, earned, bonus, redeemed, lapsed, closing.
- Cardholder details: primary holder and last 4 digits of card.

Assumptions:
1. Cardholder name appears after "Hello,"
2. Card number appears in line: "Statement for your credit card ending with XXXX"
3. Transactions are in 3-line groups:
   - Line 1: description
   - Line 2: index + amount
   - Line 3: date + Dr/Cr + RP + EMI if eligible
4. Rewards section starts with "Reward Points you have earned this month"
"""

# src/parsers/auParser.py
import logging
import pdfplumber
from src.utils.passwordHelper import openPdf
from src.parsers.parseAuRewards import parseAuRewards

logger = logging.getLogger(__name__)

def parse(filePath: str):
    logger.info(f"Opening AU PDF: {filePath}")
    with openPdf(filePath, "AU") as pdf:
        all_text = []
        for page in pdf.pages:
            all_text.extend(page.extract_text().splitlines())

    transactions = []
    rewardSummaries = []

    # --- Transaction parsing ---
    in_txn = False
    cardHolder, cardNumber, statementDate = None, None, None
    current_txn = {}

    for line in all_text:
        line = line.strip()
        if not line:
            continue

        # Card + metadata
        if line.startswith("Statement for your credit card ending with"):
            parts = line.split()
            cardNumber = parts[6].strip("()") if len(parts) > 6 else None
            statementDate = " ".join(parts[-3:])  # crude fallback
            continue
        if line.startswith("Hello, "):
            cardHolder = line.replace("Hello,", "").strip()
            continue

        # Transactions start
        if line.startswith("Your Transactions"):
            in_txn = True
            continue

        if in_txn:
            # Description line
            if not current_txn:
                current_txn["description"] = line
                continue

            # Amount line (e.g., "19 ₹4,000.00")
            if "₹" in line:
                parts = line.split()
                current_txn["index"] = parts[0]
                current_txn["amount"] = parts[1].replace("₹", "").replace(",", "")
                continue

            # Date + type + RP
            if any(tag in line for tag in ["Dr", "Cr"]):
                parts = line.split()
                current_txn["date"] = " ".join(parts[0:2])
                current_txn["type"] = "Dr" if "Dr" in parts else "Cr"
                rp_match = [p for p in parts if p.endswith("RP")]
                if rp_match:
                    current_txn["rewardPoints"] = rp_match[0].replace("RP", "")
                transactions.append(current_txn)
                current_txn = {}
                continue

    # --- Rewards ---
    rewardSummary = parseAuRewards(all_text, statementDate, cardNumber, cardHolder)
    if rewardSummary:
        rewardSummaries.append(rewardSummary)

    return transactions, rewardSummaries
