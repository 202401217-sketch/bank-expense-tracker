"""
Your own categories and remembered merchants.

Running on your own computer: everything is saved in
tracker_settings.json (next to this file), so your categories are
still there the next time you open the app.

Running as a public website: every visitor gets their own private
settings for their visit only (nothing shared between people, nothing
written to the server). Visitors keep them with the Backup / Restore
buttons in the sidebar.
"""

import json
import os
from pathlib import Path

import pandas as pd


SETTINGS_FILE = Path(__file__).with_name("tracker_settings.json")


def saves_to_disk():
    """True on your own computer, False when hosted as a website.

    Streamlit Community Cloud runs apps from /mount/src. You can also
    force it either way with the SAVE_TO_DISK environment variable
    (or a SAVE_TO_DISK = "false" line in the app's Secrets).
    """

    setting = os.environ.get("SAVE_TO_DISK", "").strip().lower()

    if setting in ("true", "1", "yes"):
        return True
    if setting in ("false", "0", "no"):
        return False

    return not str(Path(__file__).resolve()).startswith("/mount/src")

# Special category for anything you still have to decide on.
PENDING = "Needs Categorization"

# How a category is counted in the tracker.
#   Spending    -> counts towards what you spent
#   Income      -> counts as money you received
#   Not counted -> ignored (moving money between your own accounts etc.)
KINDS = ["Spending", "Income", "Not counted"]


DEFAULT_CATEGORIES = {
    "Food & Dining": "Spending",
    "Groceries": "Spending",
    "Transport": "Spending",
    "Shopping": "Spending",
    "Entertainment": "Spending",
    "Bills & Utilities": "Spending",
    "Healthcare": "Spending",
    "Education": "Spending",
    "Banking & Finance": "Spending",
    "Family": "Spending",
    "Gift": "Spending",
    "Personal": "Spending",
    "Investment": "Spending",
    "Other": "Spending",
    "Money Received": "Income",
    "Self Transfer": "Not counted",
    "Actual Transfer": "Not counted",
}


# ============================================================
# LOAD / SAVE
# ============================================================

def settings_from_json(text):
    """Read settings from JSON text. Raises ValueError if it isn't valid."""

    saved = json.loads(text)

    if not isinstance(saved, dict) or not isinstance(saved.get("categories"), dict):
        raise ValueError("This isn't a tracker settings file.")

    categories = {
        str(name).strip(): kind if kind in KINDS else "Spending"
        for name, kind in saved["categories"].items()
        if str(name).strip() and str(name).strip() != PENDING
    }

    rules = [
        {"keyword": str(r["keyword"]), "category": str(r["category"])}
        for r in saved.get("rules", [])
        if isinstance(r, dict) and r.get("keyword") and r.get("category") in categories
    ]

    return {"categories": categories or dict(DEFAULT_CATEGORIES), "rules": rules}


def settings_to_json(settings):

    return json.dumps(settings, indent=2, ensure_ascii=False)


def load_settings():

    if saves_to_disk() and SETTINGS_FILE.exists():

        try:
            return settings_from_json(SETTINGS_FILE.read_text(encoding="utf-8"))

        except (ValueError, OSError):
            # A broken settings file should never stop the app.
            pass

    return {"categories": dict(DEFAULT_CATEGORIES), "rules": []}


def save_settings(settings):

    if saves_to_disk():
        SETTINGS_FILE.write_text(settings_to_json(settings), encoding="utf-8")


# ============================================================
# MERCHANT RULES
# ============================================================
#
# A rule is {"keyword": "samyak enterprises", "category": "Groceries"}.
# Any transaction whose description CONTAINS the keyword gets that
# category. Longer (more specific) keywords win over shorter ones.

def merchant_key(description):

    return " ".join(str(description).lower().split())


def apply_rules(df, rules, categories):

    df = df.copy()
    descriptions = df["Description"].fillna("").map(merchant_key)

    for rule in sorted(rules, key=lambda r: len(r.get("keyword", ""))):

        keyword = merchant_key(rule.get("keyword", ""))
        category = rule.get("category", "")

        if not keyword or category not in categories:
            continue

        mask = descriptions.str.contains(keyword, regex=False)
        df.loc[mask, "Category"] = category

    return df


def add_rules(settings, new_rules):
    """Add or replace rules. new_rules: {keyword: category}."""

    rules = {
        merchant_key(r["keyword"]): r["category"]
        for r in settings["rules"]
        if r.get("keyword")
    }

    for keyword, category in new_rules.items():
        keyword = merchant_key(keyword)
        if keyword:
            rules[keyword] = category

    settings["rules"] = [
        {"keyword": k, "category": c} for k, c in rules.items()
    ]


# ============================================================
# PREPARE A FRESHLY UPLOADED STATEMENT
# ============================================================

def prepare_transactions(df, settings, imported=False):

    df = df.copy().reset_index(drop=True)
    categories = settings["categories"]

    if "Category" not in df.columns:
        df["Category"] = PENDING

    df["Category"] = df["Category"].fillna(PENDING).astype(str)

    if imported:
        # A CSV you exported earlier: keep your choices exactly,
        # and bring back any custom category it uses.
        for name in df["Category"].unique():
            if name != PENDING and name not in categories:
                categories[name] = "Spending"

    else:
        df = apply_rules(df, settings["rules"], categories)

    # Anything using a category that no longer exists
    # goes back to "Needs Categorization".
    valid = set(categories) | {PENDING}
    df.loc[~df["Category"].isin(valid), "Category"] = PENDING

    return df
