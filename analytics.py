"""
All numbers in the tracker come from the Category column.

Each category has a kind (Spending / Income / Not counted), so when
you change a transaction's category, every total and chart follows.
"""

import pandas as pd

from category_store import PENDING


def _kind(df, categories):

    return df["Category"].map(categories).fillna("Pending")


def _money_out(df):
    """Positive for money that left your account, negative for money in.

    So a refund (money in) that you put under "Shopping" reduces
    your Shopping spending instead of increasing it.
    """

    return df["Amount"].where(df["Type"] != "Income", -df["Amount"])


def _spending_rows(df, categories):

    rows = df[_kind(df, categories) == "Spending"].copy()
    rows["Spent"] = _money_out(rows)
    return rows


# ============================================================
# TOTALS
# ============================================================

def total_expenses(df, categories):

    return _spending_rows(df, categories)["Spent"].sum()


def total_income(df, categories):

    rows = df[_kind(df, categories) == "Income"]
    return -_money_out(rows).sum()


def total_savings(df, categories):

    return total_income(df, categories) - total_expenses(df, categories)


def pending_transactions(df):

    return df[df["Category"] == PENDING]


# ============================================================
# BREAKDOWNS
# ============================================================

def monthly_expenses(df, categories):

    rows = _spending_rows(df, categories)

    if rows.empty:
        return pd.DataFrame(columns=["Month", "Amount"])

    return (
        rows.groupby("Month")["Spent"].sum()
        .reset_index(name="Amount")
        .sort_values("Month")
    )


def category_expenses(df, categories):

    rows = _spending_rows(df, categories)

    if rows.empty:
        return pd.DataFrame(columns=["Category", "Amount"])

    result = (
        rows.groupby("Category")["Spent"].sum()
        .reset_index(name="Amount")
        .sort_values("Amount", ascending=False)
    )

    # Charts can't show negative slices (a category that is only refunds).
    return result[result["Amount"] > 0]


def monthly_category_expenses(df, categories):

    rows = _spending_rows(df, categories)

    if rows.empty:
        return pd.DataFrame(columns=["Month", "Category", "Amount"])

    return (
        rows.groupby(["Month", "Category"])["Spent"].sum()
        .reset_index(name="Amount")
    )


def category_summary(df, categories):
    """One row for EVERY category, including ones with no transactions yet."""

    money_in = df["Type"] == "Income"

    table = pd.DataFrame({
        "Category": df["Category"],
        "Money Out": df["Amount"].where(~money_in, 0),
        "Money In": df["Amount"].where(money_in, 0),
    })

    grouped = table.groupby("Category").agg(
        Transactions=("Category", "size"),
        **{
            "Money Out": ("Money Out", "sum"),
            "Money In": ("Money In", "sum"),
        },
    )

    names = list(categories) + [PENDING]
    grouped = grouped.reindex(names, fill_value=0).reset_index()
    grouped.insert(1, "Counts as", grouped["Category"].map(categories).fillna("Needs review"))

    return grouped
