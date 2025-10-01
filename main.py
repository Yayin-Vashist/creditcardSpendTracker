# main.py
import argparse
import sys
import logging
from src import dbManager
from src import billParser


def setup_logging(debug: bool):
    """Configure logging globally."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # if not debug:
        # Silence noisy libraries
    for noisy in ["pdfminer", "pdfminer.pdfpage", "pdfminer.pdfdocument"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="Credit Card Spend Tracker")
    parser.add_argument("--parse", action="store_true", help="Parse a PDF bill")
    parser.add_argument("--file", type=str, help="Path to PDF file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    setup_logging(args.debug)

    # Initialize DB
    dbManager.initDb()

    if args.parse:
        if not args.file:
            parser.error("--file argument required with --parse")

        print(f"Parsing file: {args.file}")
        insertedTx, insertedRw = billParser.parseFile(args.file)
        print(f"Inserted {insertedTx} transactions, {insertedRw} reward summaries")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user, exiting.")
        sys.exit(0)
