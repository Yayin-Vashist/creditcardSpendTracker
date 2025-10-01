import json
import os
import logging
import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

DEFAULT_PASSWORD_PATH = os.path.expanduser("~/.card-parser/passwords.json")
PASSWORD_FILE = os.getenv("CARD_PARSER_PASSWORD_FILE", DEFAULT_PASSWORD_PATH)


def loadPasswords():
    """Load the password dictionary from external JSON file."""
    if not os.path.exists(PASSWORD_FILE):
        logging.warning(f"Password file {PASSWORD_FILE} not found.")
        return {}
    try:
        with open(PASSWORD_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {PASSWORD_FILE}: {e}")
        return {}


def getPassword(bank: str, card_suffix: str | None = None) -> str | None:
    """
    Return password for given bank.
    If card_suffix is provided, look for it first.
    Otherwise fall back to 'default'.
    """
    passwords = loadPasswords()
    bank = bank.upper()
    if bank not in passwords:
        return None

    if card_suffix and card_suffix in passwords[bank]:
        return passwords[bank][card_suffix]

    return passwords[bank].get("default")


def openPdf(filePath: str, bank: str, card_suffix: str | None = None):
    """Open a PDF with the correct password for a given bank/card."""
    password = getPassword(bank, card_suffix)
    if not password:
        raise ValueError(f"No password configured for {bank} ({card_suffix or 'default'})")
    try:
        pdf = pdfplumber.open(filePath, password=password)
        logging.info(f"Opened {bank} PDF with password for card {card_suffix or 'default'}.")
        return pdf
    except PdfminerException as e:
        raise ValueError(f"Could not open {bank} PDF with stored password.") from e