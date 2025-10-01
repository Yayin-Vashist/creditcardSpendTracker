"""
Parser for ICICI Credit Card PDF Statements.

Extracts:
- Transactions: date, reference number, description, merchant code, amount, credit/debit
- Cardholder details: masked card number (used to distinguish primary/add-on)

Notes (based on observed ICICI statements):
1. Card number line looks like: "6528XXXXXXXX1005"
2. Transaction rows look like:
   "04/08/2025 11725387534 BBPS Payment received 0 10.00 CR"
   or
   "10/08/2025 11770955856 Myntra 111 5,552.36"
   Columns:
     date | reference | description | merchantCode | amount | CR (optional)
3. No reward points block like HDFC/SBI.
"""

import pdfplumber
import re
import logging
from typing import List, Dict, Tuple
from src.utils.passwordHelper import getPassword

logger = logging.getLogger(__name__)

def parse(filePath: str) -> Tuple[List[Dict], List[Dict]]:
    transactions: List[Dict] = []
    rewardSummaries: List[Dict] = []

    currentCardNumber = None
    statementDate = None  # optional, if found in header

    password = getPassword("ICICI")  # 🔑 fetch from passwords.json
    logger.info(f"Opening ICICI PDF: {filePath} (password protected)")

    with pdfplumber.open(filePath, password=password) as pdf:
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

                logger.debug(f"Line: {line}")

                # --- Detect card number line ---
                if re.match(r"\d{4}X{8}\d{4}", line):
                    currentCardNumber = line.strip()
                    logger.info(f"Found card number: {currentCardNumber}")
                    continue

                # --- Detect transaction line ---
                txMatch = re.match(
                    r"(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(.*?)\s+(\d+)\s+([\d,]+\.\d{2})(?:\s+(CR))?",
                    line,
                )
                if txMatch and currentCardNumber:
                    date = txMatch.group(1)
                    reference = txMatch.group(2)
                    description = txMatch.group(3).strip()
                    merchantCode = txMatch.group(4)
                    amount = float(txMatch.group(5).replace(",", ""))
                    creditFlag = txMatch.group(6)

                    transactionType = "CREDIT" if creditFlag == "CR" else "DEBIT"

                    transactions.append({
                        "date": date,
                        "referenceNumber": reference,
                        "description": description,
                        "merchantCode": merchantCode,
                        "amount": amount,
                        "currency": "INR",
                        "transactionType": transactionType,
                        "cardNumber": currentCardNumber,
                        "cardHolderName": None,  # not in ICICI statement
                        "sourceBank": "ICICI",
                        "statementDate": statementDate,
                        "category": None,
                        "subCategory": None,
                        "parserUsed": "iciciParser",
                        "importId": None,
                    })

                    logger.debug(
                        f"Parsed transaction: {date} | {reference} | {description} | "
                        f"{merchantCode} | {amount} | {transactionType}"
                    )

    return transactions, rewardSummaries