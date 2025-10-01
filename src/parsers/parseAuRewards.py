# src/parsers/auRewardsHelper.py
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def extractInt(line: str) -> Optional[int]:
    """Return first integer in a line, or None if not found."""
    m = re.search(r"(\d[\d,]*)", line)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def parseAuRewards(lines: List[str], statementDate: Optional[str], cardNumber: Optional[str], cardHolder: Optional[str]) -> Dict:
    """
    Parse AU Credit Card reward summary.
    Normalized to match SBI/HDFC reward schema.
    """
    in_section = False
    earned = 0
    bonus = 0
    rewards = {
        "statementDate": statementDate,
        "cardNumber": cardNumber,
        "cardHolderName": cardHolder,
        "openingBalance": None,
        "earned": None,           # earned + bonus
        "redeemed": None,
        "adjustedLapsed": None,
        "closingBalance": None,
        "parserUsed": "auParser",
        "importId": None,
    }

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Reward Points you have earned this month"):
            in_section = True
            continue

        if not in_section:
            continue

        # Stop when section ends
        if line.startswith("Fuel Surcharge") or line.startswith("Page "):
            break

        if line.startswith("Opening balance"):
            rewards["openingBalance"] = extractInt(line)

        elif line.startswith("Earned +"):
            val = extractInt(line)
            if val is not None:
                earned = val

        elif line.startswith("Bonus Points"):
            val = extractInt(line)
            if val is not None:
                bonus = val

        elif line.startswith("Lapsed"):
            rewards["adjustedLapsed"] = extractInt(line)

        elif line.startswith("Redeemed"):
            rewards["redeemed"] = extractInt(line)

        elif line.startswith("Total reward points"):
            rewards["closingBalance"] = extractInt(line)

    # Merge earned + bonus
    if earned or bonus:
        rewards["earned"] = (earned or 0) + (bonus or 0)

    if rewards["closingBalance"] is not None:
        logger.info("AU reward summary parsed (normalized schema)")
        return rewards

    logger.warning("AU reward summary not found")
    return {}
