import json
import logging
import os
import re
import pandas as pd # Assuming pandas is available
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

CONFIG_DIR = "config"
CATEGORIES_FILE = os.path.join(CONFIG_DIR, "categories.json")
CATEGORY_RULES_FILE = os.path.join(CONFIG_DIR, "categoryRules.json")
UNCATEGORIZED_LOG = "logs/unparsedTransactions.csv"

# --- Utility Functions ---

def loadJsonFile(filePath: str) -> Dict:
    if not os.path.exists(os.path.dirname(filePath)):
        logger.error(f"Config directory '{os.path.dirname(filePath)}' not found.")
        return {}
    if not os.path.exists(filePath):
        logger.warning(f"Config file {filePath} not found.")
        return {}
    try:
        with open(filePath, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {filePath}: {e}")
        return {}

def _log_uncategorized(transactions: List[Dict]):
    """Logs transactions with 'category': 'Uncategorized' to a CSV file."""
    uncat_data = [tx for tx in transactions if tx.get("category") == "Uncategorized"]
    if uncat_data:
        os.makedirs(os.path.dirname(UNCATEGORIZED_LOG), exist_ok=True)
        pd.DataFrame(uncat_data).to_csv(UNCATEGORIZED_LOG, index=False)
        logger.info(f"{len(uncat_data)} transactions uncategorized. Logged to {UNCATEGORIZED_LOG}")

# --- Core Setup Function ---

def _setup_categorizer() -> tuple[List[tuple[str, Dict]], List[Dict]]:
    """Loads, sorts merchants, and pre-compiles regex rules for efficiency."""
    
    # 1. Merchant Setup
    categories = loadJsonFile(CATEGORIES_FILE)
    # Sort merchants by length descending for best-match prioritization
    sorted_merchants = sorted(
        categories.items(), 
        key=lambda item: len(item[0]), 
        reverse=True
    )
    
    # 2. Rule Setup & Pre-compilation
    rules_data = loadJsonFile(CATEGORY_RULES_FILE)
    processed_rules = []
    
    for pattern, rule_data in rules_data.items():
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}. Skipping rule.")
            continue

        # Normalize rule_data: { 'DEBIT': rule, 'CREDIT': rule }
        normalized_rule = {}
        if isinstance(rule_data, dict) and any(k in rule_data for k in ['DEBIT', 'CREDIT']):
            # Type-specific rule structure
            normalized_rule['DEBIT'] = rule_data.get('DEBIT')
            normalized_rule['CREDIT'] = rule_data.get('CREDIT')
        else:
            # General rule: apply to both types
            normalized_rule['DEBIT'] = rule_data
            normalized_rule['CREDIT'] = rule_data
            
        processed_rules.append({
            "compiled_pattern": compiled_pattern,
            "rule": normalized_rule
        })
        
    return sorted_merchants, processed_rules

# --- Main Logic ---

def categorizeTransactions(transactions: List[Dict]) -> List[Dict]:
    """
    Categorize transactions using pre-processed merchant names (longest first) 
    and pre-compiled, type-aware regex rules.
    """
    
    sorted_merchants, processed_rules = _setup_categorizer()
    
    for tx in transactions:
        desc_lower = tx.get("description", "").lower()
        tx_type = tx.get("transactionType", "DEBIT").upper()
        matched = False
        
        # 1️⃣ Substring merchant match (Prioritized)
        for merchant_name, cat_info in sorted_merchants:
            if merchant_name.lower() in desc_lower:
                tx["category"] = cat_info.get("category")
                tx["subCategory"] = cat_info.get("subCategory")
                matched = True
                break
        
        # 2️⃣ Pre-compiled Regex / keyword rules
        if not matched: 
            for rule_entry in processed_rules:
                if rule_entry["compiled_pattern"].search(desc_lower):
                    
                    final_cat_rule = rule_entry["rule"].get(tx_type) 
                    
                    if isinstance(final_cat_rule, dict):
                        tx["category"] = final_cat_rule.get("category")
                        tx["subCategory"] = final_cat_rule.get("subCategory")
                        matched = True
                        break

        # 3️⃣ Fallback to a specific string
        if not matched:
            tx["category"] = "Uncategorized" 
            tx["subCategory"] = "Needs Review"

    _log_uncategorized(transactions)

    return transactions