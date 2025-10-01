import sqlite3
from typing import List, Dict

DB_PATH = "data/db.sqlite"

def initDb():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Transactions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        description TEXT,
        merchant TEXT,
        amount REAL,
        currency TEXT,
        transactionType TEXT,
        rewardPoints INTEGER,
        cardNumber TEXT,
        cardHolderName TEXT,
        sourceBank TEXT,
        statementDate TEXT,
        category TEXT,
        subCategory TEXT,
        parserUsed TEXT,
        importId TEXT,
        UNIQUE (date, description, amount, transactionType, cardHolderName)
    )
    """)

    # Reward Points Summary table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rewardPointsSummary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        statementDate TEXT,
        cardNumber TEXT,
        cardHolderName TEXT,
        openingBalance INTEGER,
        earned INTEGER,
        redeemed INTEGER,
        adjustedLapsed INTEGER,
        closingBalance INTEGER,
        parserUsed TEXT,
        importId TEXT,
        UNIQUE (statementDate, cardNumber)
    )
    """)

    conn.commit()
    conn.close()


def insertTransactions(transactions: List[Dict]) -> int:
    """Insert list of transaction dicts into DB, return number inserted (ignores duplicates)."""
    if not transactions:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        rows = [
            (
                tx.get("date"),
                tx.get("description"),
                tx.get("merchant"),
                float(tx.get("amount")) if tx.get("amount") else None,
                tx.get("currency"),
                tx.get("transactionType"),
                int(tx.get("rewardPoints")) if tx.get("rewardPoints") else None,
                tx.get("cardNumber"),
                tx.get("cardHolderName"),
                tx.get("sourceBank"),
                tx.get("statementDate"),
                tx.get("category"),
                tx.get("subCategory"),
                tx.get("parserUsed", "genericPdfParser"),
                tx.get("importId"),
            )
            for tx in transactions
        ]
        cur.executemany("""
            INSERT OR IGNORE INTO transactions (
                date, description, merchant, amount, currency,
                transactionType, rewardPoints, cardNumber, cardHolderName,
                sourceBank, statementDate, category, subCategory,
                parserUsed, importId
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        return cur.rowcount  # only count successfully inserted rows
    except Exception as e:
        print("DB insert error:", e)
        return 0
    finally:
        conn.close()


def insertRewardSummary(summaries: List[Dict]) -> int:
    """Insert list of reward summary dicts into DB, return number inserted (ignores duplicates)."""
    if not summaries:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        rows = [
            (
                s.get("statementDate"),
                s.get("cardNumber"),
                s.get("cardHolderName"),
                int(s.get("openingBalance")) if s.get("openingBalance") else None,
                int(s.get("earned")) if s.get("earned") else None,
                int(s.get("redeemed")) if s.get("redeemed") else None,
                int(s.get("adjustedLapsed")) if s.get("adjustedLapsed") else None,
                int(s.get("closingBalance")) if s.get("closingBalance") else None,
                s.get("parserUsed", "genericPdfParser"),
                s.get("importId"),
            )
            for s in summaries
        ]
        cur.executemany("""
            INSERT OR IGNORE INTO rewardPointsSummary (
                statementDate, cardNumber, cardHolderName,
                openingBalance, earned, redeemed, adjustedLapsed,
                closingBalance, parserUsed, importId
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print("DB reward insert error:", e)
        return 0
    finally:
        conn.close()