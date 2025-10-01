# ========================= src/parsers/genericPdfParser.py =========================
import pdfplumber
from typing import List, Dict
import re




def parse(filePath: str) -> List[Dict]:
    """
    Very simple placeholder parser.
    Extracts lines that look like transactions: DATE DESCRIPTION AMOUNT
    Format will vary per bank; adjust regex rules as needed.
    """
    transactions = []
    with pdfplumber.open(filePath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                # print("LINE:", repr(line))  # debug
                # Example regex: date dd-mm-yyyy, description words, amount at end
                match = re.match(r"(\d{2}-\d{2}-\d{4})\s+(.+)\s+(-?\d+\.\d{2})", line)
                if match:
                    date, description, amount = match.groups()
                    tx = {
                    "date": date,
                    "description": description.strip(),
                    "merchant": description.split()[0],
                    "amount": float(amount),
                    "currency": "INR",
                    "cardNumber": None,
                    "sourceBank": "Unknown",
                    "sourceEmail": None,
                    "category": None,
                    "subCategory": None,
                    "parserUsed": "genericPdfParser",
                    "importId": None,
                    }
                    transactions.append(tx)
    return transactions