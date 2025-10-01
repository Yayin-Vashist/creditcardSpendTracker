# src/parsers/hdfcParser.py
"""
HDFC Credit Card PDF Parser
---------------------------
This parser extracts:
1. Transactions (date, description, amount, type, reward points, cardholder).
2. Reward Points Summary (opening, earned, redeemed, adjusted, closing).

Notes:
- HDFC statements sometimes show primary & add-on cardholders.
- Primary holder is usually in ALL CAPS, add-on in Title Case.
- Reward summaries are shown in a block with "Points Earned".
"""

import pdfplumber
import re
from typing import List, Dict, Tuple

# Headers / sections to ignore when detecting cardholder names
EXCLUDE_HEADERS = {
    "DOMESTIC TRANSACTIONS",
    "INTERNATIONAL TRANSACTIONS",
    "REWARD POINTS",
    "STATEMENT",
    "PAYMENT DUE",
    "CREDIT SUMMARY",
    "POINTS EARNED",
    "TOTAL CREDIT LIMIT",
    "IMPORTANT INFORMATION",
    "DETAILS",
    "NEW DELHI",   # Example of location that gets mistaken as a name
}


def looks_like_cardholder(line: str) -> bool:
    """
    Detect whether a line looks like a cardholder name.
    Rules:
    - Not in exclude headers
    - Must not contain digits, slashes, or colons
    - Primary: ALL CAPS, <= 4 words
    - Add-on: Title Case (e.g., "John Doe")
    """
    clean = line.strip()
    upper = clean.upper()

    if upper in EXCLUDE_HEADERS:
        return False
    if any(c in clean for c in ["/", ":", "|"]):
        return False
    if any(ch.isdigit() for ch in clean):
        return False

    # Primary cardholder (all caps short name)
    if clean.isupper() and len(clean.split()) <= 4:
        return True

    # Add-on cardholder (title case short name)
    if clean.istitle() and len(clean.split()) <= 4:
        return True

    return False


def parse(filePath: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Parse HDFC PDF statement and return:
    - transactions: list of transaction dicts
    - rewardSummaries: list of reward summary dicts
    """
    transactions: List[Dict] = []
    rewardSummaries: List[Dict] = []

    # Track current state while parsing
    currentCardHolder = None
    primaryCardHolder = None
    statementDate = None

    # Reward summary fields
    opening = earned = redeemed = adjusted = closing = None

    with pdfplumber.open(filePath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.splitlines():
                line = line.strip()

                # --- Capture statement date ---
                stmtMatch = re.search(
                    r"(Statement|Billing) Date\s+(\d{1,2}\s\w+,\s\d{4})", line
                )
                if stmtMatch:
                    statementDate = stmtMatch.group(2)

                # --- Detect cardholder name ---
                # print("Before : ", primaryCardHolder, currentCardHolder, statementDate)

                if looks_like_cardholder(line):
                    if line.isupper() and not primaryCardHolder:
                        # First ALL CAPS name is primary
                        primaryCardHolder = line
                    currentCardHolder = line

                # print("After : ", primaryCardHolder, currentCardHolder, statementDate)

                # --- Detect transaction line ---
                txMatch = re.match(
                    r"(\d{2}/\d{2}/\d{4}).*?C\s([\d,]+\.\d{2})", line
                )
                if txMatch:
                    date = txMatch.group(1)
                    amount = float(txMatch.group(2).replace(",", ""))

                    transactionType = "DEBIT"
                    rewardPoints = None

                    # If reward points inline: "+ 20 C 860.00"
                    rpMatch = re.search(r"\+\s*(\d+)\s*C\s", line)
                    if rpMatch:
                        rewardPoints = int(rpMatch.group(1))

                    # If explicitly a credit transaction
                    if "+ C" in line:
                        transactionType = "CREDIT"

                    transactions.append({
                        "date": date,
                        "description": line.split("|")[1].strip() if "|" in line else line,
                        "merchant": None,  # TODO: parse merchant separately
                        "amount": amount,
                        "currency": "INR",
                        "transactionType": transactionType,
                        "rewardPoints": rewardPoints,
                        "cardNumber": None,  # Not available in HDFC PDF
                        "cardHolderName": currentCardHolder,
                        "sourceBank": "HDFC",
                        "statementDate": statementDate,
                        "category": None,
                        "subCategory": None,
                        "parserUsed": "hdfcParser",
                        "importId": None,
                    })

                # --- Detect reward summary lines ---
                if "Points Earned" in line:
                    # Closing balance appears here
                    try:
                        closing = int(line.split()[0].replace(",", ""))
                    except (ValueError, IndexError):
                        pass

                elif re.match(
                    r"^\d{1,3}(,\d{3})*\s+\d{1,3}(,\d{3})*\s+\d{1,3}(,\d{3})*\s+\d{1,3}(,\d{3})*$",
                    line,
                ):
                    # This line has opening, earned, redeemed, adjusted
                    try:
                        parts = [int(x.replace(",", "")) for x in line.split()]
                        if len(parts) == 4:
                            opening, earned, redeemed, adjusted = parts
                    except (ValueError, IndexError):
                        pass

        if primaryCardHolder is None:
            primaryCardHolder = "PRIMARY CARDHOLDER"  # fallback

        if all(v is not None for v in [opening, earned, redeemed, adjusted, closing]):
            rewardSummaries.append({
                "statementDate": statementDate,
                "cardNumber": None,
                "cardHolderName": primaryCardHolder,
                "openingBalance": opening,
                "earned": earned,
                "redeemed": redeemed,
                "adjustedLapsed": adjusted,
                "closingBalance": closing,
                "parserUsed": "hdfcParser",
                "importId": None,
            })


    return transactions, rewardSummaries
