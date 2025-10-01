import logging
import re
import uuid

logger = logging.getLogger(__name__)

def parseRewards(lines, statementPeriod, cardNumber, cardHolderName):
    """
    Parse SBI rewards summary section.

    Expected line format:
        <openingBalance> <earned> <redeemed> <adjustedLapsed> <closingBalance|NONE>

    Example:
        "1968 158 2000 126 NONE"

    Returns:
        list of dicts (to be consistent with other parsers).
    """
    rewardSummaries = []

    for line in lines:
        tokens = line.strip().split()
        if len(tokens) == 5 and tokens[0].isdigit() and tokens[1].isdigit():
            try:
                openingBalance = int(tokens[0])
                earned = int(tokens[1])
                redeemed = int(tokens[2])
                adjustedLapsed = int(tokens[3])
                closingBalance = 0 if tokens[4].upper() == "NONE" else int(tokens[4])

                rewardSummaries.append({
                    "statementDate": statementPeriod.split("to")[-1].strip(),  # use end date
                    "cardNumber": cardNumber,
                    "cardHolderName": cardHolderName,
                    "openingBalance": openingBalance,
                    "earned": earned,
                    "redeemed": redeemed,
                    "adjustedLapsed": adjustedLapsed,
                    "closingBalance": closingBalance,
                    "parserUsed": "sbiParser",
                    "importId": str(uuid.uuid4())
                })

                logger.info(f"Parsed SBI reward summary: OB={openingBalance}, Earned={earned}, "
                            f"Redeemed={redeemed}, Lapsed={adjustedLapsed}, CB={closingBalance}")
                break  # usually one summary per statement
            except Exception as e:
                logger.error(f"Error parsing reward summary line '{line}': {e}")

    if not rewardSummaries:
        logger.warning("No reward summary found in SBI statement.")

    return rewardSummaries