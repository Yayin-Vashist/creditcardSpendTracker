# src/rewardValidator.py
"""
Reward Summary Validator

Validates credit card reward summaries to ensure:
    openingBalance + earned - redeemed - adjustedLapsed == closingBalance

Features:
- Safe integer parsing (handles None, blanks, commas)
- Detects missing/incomplete fields
- Logs validation issues into CSV for audit
- Prints concise console summary
"""

import csv
import os
from typing import Dict, List, Tuple, Optional

LOG_PATH = "logs/rewardValidationWarnings.csv"


def _toIntSafe(v) -> Optional[int]:
    """Convert a value (possibly string with commas) to int. Return None on failure."""
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
    Validate a single reward summary.

    Returns:
        (isValid, message)
        - isValid = True if the summary matches the expected closing balance
        - message = empty if valid, otherwise an explanation
    """
    opening = _toIntSafe(summary.get("openingBalance"))
    earned = _toIntSafe(summary.get("earned"))
    redeemed = _toIntSafe(summary.get("redeemed"))
    adjusted = _toIntSafe(summary.get("adjustedLapsed"))
    closing = _toIntSafe(summary.get("closingBalance"))

    # If any critical value is missing, validation is incomplete
    if any(x is None for x in [opening, earned, redeemed, adjusted, closing]):
        missing = []
        if opening is None: missing.append("openingBalance")
        if earned is None: missing.append("earned")
        if redeemed is None: missing.append("redeemed")
        if adjusted is None: missing.append("adjustedLapsed")
        if closing is None: missing.append("closingBalance")
        return False, f"incomplete_fields: {','.join(missing)}"

    expected = opening + earned - redeemed - adjusted
    if expected == closing:
        return True, ""
    else:
        return False, (
            f"mismatch: expected_closing={expected}, actual_closing={closing} "
            f"[opening={opening}, earned={earned}, redeemed={redeemed}, adjusted={adjusted}]"
        )


def validateAndLogRewardSummaries(
    summaries: List[Dict],
    logPath: str = LOG_PATH,
    overwrite: bool = False
) -> List[Tuple[Dict, str]]:
    """
    Validate multiple reward summaries.
    Writes issues to CSV (append by default, overwrite if specified).
    
    Args:
        summaries : list of dicts
        logPath   : CSV file to store validation warnings
        overwrite : if True, clear file before writing

    Returns:
        List of (summary, message) for invalid entries.
        Valid ones have message == "".
    """
    os.makedirs(os.path.dirname(logPath), exist_ok=True)
    warnings = []

    header = [
        "statementDate", "cardNumber", "cardHolderName",
        "openingBalance", "earned", "redeemed", "adjustedLapsed",
        "closingBalance", "issue"
    ]

    mode = "w" if overwrite else "a"
    with open(logPath, mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if overwrite or csvfile.tell() == 0:
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
                    message,
                ])

    # Print concise feedback
    if warnings:
        print(f"Reward validation: {len(warnings)} issue(s) found — see {logPath}")
        for s, msg in warnings:
            print(f"  - [{s.get('statementDate','Unknown')}] {s.get('cardHolderName','Unknown')}: {msg}")
    else:
        print("Reward validation: all summaries valid ✅")

    return warnings
