# src/validator.py
"""
Validator utilities for parsed data.
Includes reward-summary validation:
    opening + earned - redeemed - adjusted == closing
"""

import csv
import os
from typing import Dict, List, Tuple, Optional


LOG_PATH = "logs/rewardValidationWarnings.csv"


def _toIntSafe(v) -> Optional[int]:
    """Try to convert a value (possibly with commas) to int. Return None on failure."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    try:
        s = str(v).replace(",", "").strip()
        return int(s)
    except Exception:
        return None


def validateRewardSummary(summary: Dict) -> Tuple[bool, str]:
    """
    Validate a single reward summary dict.
    Returns (isValid, message). Message empty when valid, otherwise explains difference.
    Expects keys: openingBalance, earned, redeemed, adjustedLapsed, closingBalance.
    """
    opening = _toIntSafe(summary.get("openingBalance"))
    earned = _toIntSafe(summary.get("earned"))
    redeemed = _toIntSafe(summary.get("redeemed"))
    adjusted = _toIntSafe(summary.get("adjustedLapsed"))
    closing = _toIntSafe(summary.get("closingBalance"))

    # If any critical value is missing, we cannot validate strictly
    if any(x is None for x in [opening, earned, redeemed, adjusted, closing]):
        missing = []
        if opening is None:
            missing.append("openingBalance")
        if earned is None:
            missing.append("earned")
        if redeemed is None:
            missing.append("redeemed")
        if adjusted is None:
            missing.append("adjustedLapsed")
        if closing is None:
            missing.append("closingBalance")
        return False, f"incomplete_fields: {','.join(missing)}"

    expected = opening + earned - redeemed - adjusted
    if expected == closing:
        return True, ""
    else:
        return False, f"mismatch: expected_closing={expected}, actual_closing={closing}"


def validateAndLogRewardSummaries(summaries: List[Dict], logPath: str = LOG_PATH) -> List[Tuple[Dict, str]]:
    """
    Validate a list of reward summaries. Writes warnings to CSV and returns list of (summary, message)
    for each invalid summary. Valid summaries have message == "".
    """
    os.makedirs(os.path.dirname(logPath), exist_ok=True)

    warnings = []  # list of (summary, message) for invalid ones
    # Prepare CSV header
    header = [
        "statementDate", "cardNumber", "cardHolderName",
        "openingBalance", "earned", "redeemed", "adjustedLapsed",
        "closingBalance", "issue"
    ]

    # We'll append warnings to the CSV (create if not exists)
    with open(logPath, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # If file empty, write header (simple check)
        if csvfile.tell() == 0:
            writer.writerow(header)

        for s in summaries:
            isValid, message = validateRewardSummary(s)
            if not isValid:
                warnings.append((s, message))
                writer.writerow([
                    s.get("statementDate"),
                    s.get("cardNumber"),
                    s.get("cardHolderName"),
                    s.get("openingBalance"),
                    s.get("earned"),
                    s.get("redeemed"),
                    s.get("adjustedLapsed"),
                    s.get("closingBalance"),
                    message
                ])

    # Print a concise summary
    if warnings:
        print(f"Reward validation: {len(warnings)} issue(s) found — details written to {logPath}")
        for s, msg in warnings:
            print(f"  - [{s.get('statementDate')}] {s.get('cardHolderName')}: {msg}")
    else:
        print("Reward validation: all summaries valid.")

    return warnings