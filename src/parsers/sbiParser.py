# src/parsers/sbiParser.py
"""
Parser for SBI Credit Card PDF Statements.

Extracts:
- Transactions: date, description, amount, credit/debit, etc.
- Reward summary: opening, earned, redeemed, lapsed, closing.
- Cardholder details: primary holder and masked card number.

Assumptions (based on observed SBI statements):
1. Cardholder name appears like: "YAYIN VASHIST Credit Card Number"
2. Card number appears on the next line as: "XXXX XXXX XXXX XX51"
3. Reward summary numbers are a block of 5 values:
   [opening, earned, redeemed, closing, lapsed]
4. Transactions table starts after line: "Date Transaction Details Amount ( ` )"
5. Transaction rows look like:
   "12 Aug 25 UPI-Swiggy Instamart 326.00 D"
   Columns: date | description | amount | D/C
"""

import pdfplumber
import re
from typing import List, Dict, Tuple
import logging
from src.parsers.sbiRewardsHelper import parseRewards
import os
import hashlib
from datetime import datetime

def generateImportId(filePath: str, statementDate: str) -> str:
    """Generate a unique ID for this statement."""
    base = f"{os.path.basename(filePath)}_{statementDate}"
    return hashlib.md5(base.encode()).hexdigest()


logger = logging.getLogger(__name__)


def parse(filePath: str) -> Tuple[List[Dict], List[Dict]]:
    transactions: List[Dict] = []
    rewardSummaries: List[Dict] = []

    primaryCardHolder = None
    cardNumber = None
    statementDate = None

    opening = earned = redeemed = lapsed = closing = None
    insideTransactions = False

    logger.info(f"Opening SBI PDF: {filePath}")

    with pdfplumber.open(filePath) as pdf:
        for pageNum, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                logger.warning(f"Page {pageNum} has no extractable text")
                continue

            lines = text.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # --- Cardholder name ---
                if "Credit Card Number" in line and not primaryCardHolder:
                    primaryCardHolder = line.split(" Credit Card Number")[0].strip()
                    logger.info(f"Found cardholder name: {primaryCardHolder}")

                # --- Card number ---
                if re.match(r"X{4}\sX{4}\sX{4}\sXX\d{2}", line) and not cardNumber:
                    cardNumber = line.strip()
                    logger.info(f"Found masked card number: {cardNumber}")

                # --- Statement period ---
                stmtMatch = re.search(r"for Statement Period:\s*(.+)", line)
                if stmtMatch and not statementDate:
                    statementDate = stmtMatch.group(1)
                    logger.info(f"Found statement period: {statementDate}")

                # Import ID generation
                importId = generateImportId(filePath, statementDate)

                # --- Reward summary block (5 numbers) ---
                if re.match(r"^(\d+[ ,]*){5}$", line.replace(",", "")):
                    try:
                        parts = [int(x.replace(",", "")) for x in line.split()]
                        if len(parts) == 5:
                            opening, earned, redeemed, closing, lapsed = parts
                            logger.info(
                                f"Reward summary found: opening={opening}, "
                                f"earned={earned}, redeemed={redeemed}, "
                                f"closing={closing}, lapsed={lapsed}"
                            )
                    except Exception as e:
                        logger.error(f"Failed to parse reward summary: {line} ({e})")

                # --- Start of transactions ---
                if line.startswith("Date Transaction Details Amount"):
                    insideTransactions = True
                    logger.info("Detected start of transaction table")
                    continue

                if insideTransactions:
                    txMatch = re.match(
                        r"(\d{2}\s\w{3}\s\d{2})\s+(.*?)\s+([\d,]+\.\d{2})\s+([DC])$",
                        line,
                    )
                    if txMatch:
                        date_str = txMatch.group(1)                  # "12 Aug 25"
                        try:
                            date = datetime.strptime(date_str, "%d %b %y").date()  # → 2025-08-12
                        except ValueError as e:
                            logger.warning(f"Failed to parse transaction date: {date_str} ({e})")
                            date = None
                        desc = txMatch.group(2).strip()
                        amount = float(txMatch.group(3).replace(",", ""))
                        dcFlag = txMatch.group(4)
                        transactionType = "DEBIT" if dcFlag == "D" else "CREDIT"

                        transactions.append({
                            "date": date,
                            "description": desc,
                            "merchant": None,
                            "amount": amount,
                            "currency": "INR",
                            "transactionType": transactionType,
                            "rewardPoints": None,
                            "cardNumber": cardNumber,
                            "cardHolderName": primaryCardHolder,
                            "sourceBank": "SBI",
                            "statementDate": statementDate,
                            "category": None,
                            "subCategory": None,
                            "parserUsed": "sbiParser",
                            "importId": importId,
                        })

                        logger.debug(
                            f"Parsed transaction: {date} | {desc} | {amount} | {transactionType}"
                        )

            # --- Append reward summary (if found) ---
            rewardSummaries = rewardSummaries + parseRewards(lines, statementDate, cardNumber, primaryCardHolder)

    if opening is not None:
        rewardSummaries.append({
            "statementDate": statementDate,
            "cardNumber": cardNumber,
            "cardHolderName": primaryCardHolder,
            "openingBalance": opening,
            "earned": earned,
            "redeemed": redeemed,
            "adjustedLapsed": lapsed,
            "closingBalance": closing,
            "parserUsed": "sbiParser",
            "importId": importId,
        })
        logger.info("Reward summary added to parsed data")

    return transactions, rewardSummaries
    transactions: List[Dict] = []
    rewardSummaries: List[Dict] = []

    primaryCardHolder = None
    cardNumber = None
    statementDate = None  # SBI often has "for Statement Period: 12 Aug 25 to 11 Sep 25"

    opening = earned = redeemed = lapsed = closing = None
    insideTransactions = False

    with pdfplumber.open(filePath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.splitlines()
            for line in lines:
                line = line.strip()

                # --- Cardholder name ---
                if "Credit Card Number" in line and not primaryCardHolder:
                    primaryCardHolder = line.split(" Credit Card Number")[0].strip()

                # --- Card number ---
                if re.match(r"X{4}\sX{4}\sX{4}\sXX\d{2}", line) and not cardNumber:
                    cardNumber = line.strip()

                # --- Statement period ---
                stmtMatch = re.search(r"for Statement Period:\s*(.+)", line)
                if stmtMatch:
                    statementDate = stmtMatch.group(1)

                # --- Reward summary block (5 numbers in one line) ---
                if re.match(r"^(\d+[ ,]*){5}$", line.replace(",", "")):
                    try:
                        parts = [int(x.replace(",", "")) for x in line.split()]
                        if len(parts) == 5:
                            opening, earned, redeemed, closing, lapsed = parts
                    except Exception:
                        pass

                # --- Start of transactions ---
                if line.startswith("Date Transaction Details Amount"):
                    insideTransactions = True
                    continue

                if insideTransactions:
                    # Transaction row: "12 Aug 25 <desc> <amount> D/C"
                    txMatch = re.match(r"(\d{2}\s\w{3}\s\d{2})\s+(.*?)\s+([\d,]+\.\d{2})\s+([DC])$", line)
                    if txMatch:
                        date = txMatch.group(1)
                        desc = txMatch.group(2).strip()
                        amount = float(txMatch.group(3).replace(",", ""))
                        dcFlag = txMatch.group(4)

                        transactionType = "DEBIT" if dcFlag == "D" else "CREDIT"

                        transactions.append({
                            "date": date,
                            "description": desc,
                            "merchant": None,
                            "amount": amount,
                            "currency": "INR",
                            "transactionType": transactionType,
                            "rewardPoints": None,
                            "cardNumber": cardNumber,
                            "cardHolderName": primaryCardHolder,
                            "sourceBank": "SBI",
                            "statementDate": statementDate,
                            "category": None,
                            "subCategory": None,
                            "parserUsed": "sbiParser",
                            "importId": None,
                        })

    # --- Append reward summary (if found) ---
    if opening is not None:
        rewardSummaries.append({
            "statementDate": statementDate,
            "cardNumber": cardNumber,
            "cardHolderName": primaryCardHolder,
            "openingBalance": opening,
            "earned": earned,
            "redeemed": redeemed,
            "adjustedLapsed": lapsed,
            "closingBalance": closing,
            "parserUsed": "sbiParser",
            "importId": None,
        })

    return transactions, rewardSummaries