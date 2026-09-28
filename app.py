from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

from parser import parse_statement
from donut_chart import show_donut

from category_store import (
    PENDING,
    KINDS,
    load_settings,
    save_settings,
    saves_to_disk,
    settings_from_json,
    settings_to_json,
    add_rules,
    apply_rules,
    merchant_key,
    prepare_transactions,
)

from analytics import (
    total_income,
    total_expenses,
    total_savings,
    pending_transactions,
    monthly_expenses,
    category_expenses,
    monthly_category_expenses,
    category_summary,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Bank Expense Tracker",
    page_icon="💰",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================
#
# base_df        -> the transactions table the editor starts from
# editor_version -> bumped whenever we change base_df ourselves,
#                   so the editor redraws with the new values

if "settings" not in st.session_state:
    st.session_state.settings = load_settings()

if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0

settings = st.session_state.settings
categories = settings["categories"]


def persist():
    save_settings(settings)


def commit(df, message=None):
    """Make df the new starting table and redraw the page."""

    if df is not None:
        st.session_state.base_df = df.reset_index(drop=True)

    st.session_state.editor_version += 1

    if message:
        st.session_state.flash = message

    st.rerun()


# ============================================================
# TITLE
# ============================================================

st.title("💰 Bank Expense Tracker")

st.write(
    "Upload your bank statement, then set the category of any "
    "transaction. Every total and chart updates from your categories."
)

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "Upload your bank statement (or a CSV you exported from this app)",
    type=["pdf", "csv", "xlsx", "xls"]
)

st.caption(
    "🔒 Your statement is only read in memory to build your dashboard. "
    "It is never saved on the server."
)

SAMPLE_FILE = Path(__file__).with_name("sample_data") / "sample_statement.csv"

if uploaded_file:
    st.session_state.use_sample = False

elif st.session_state.get("use_sample"):
    st.info("You're looking at **sample data**. Upload your own statement above anytime.")
    if st.button("✖ Close sample data"):
        st.session_state.use_sample = False
        st.session_state.pop("file_key", None)
        st.rerun()

source_name = (
    f"{uploaded_file.name}-{uploaded_file.size}" if uploaded_file
    else "sample" if st.session_state.get("use_sample")
    else None
)

edited_df = None


if source_name:

    # --------------------------------------------------------
    # PARSE (only once per file, so your edits aren't lost)
    # --------------------------------------------------------

    file_key = source_name

    if st.session_state.get("file_key") != file_key:

        with st.spinner("Reading your bank statement..."):

            try:
                if uploaded_file:
                    df = parse_statement(uploaded_file)
                else:
                    with open(SAMPLE_FILE, "rb") as sample:
                        df = parse_statement(sample)

            except Exception as error:
                st.error(f"Could not read the statement: {error}")
                st.stop()

        if df.empty:
            st.error("No transactions could be detected.")
            st.stop()

        imported = df.attrs.get("tracker_export", False)
        df = prepare_transactions(df, settings, imported=imported)

        if imported:
            persist()  # keeps any custom categories found in the file

        st.session_state.file_key = file_key
        st.session_state.base_df = df
        st.session_state.remembered = df["Category"].copy()
        st.session_state.editor_version += 1

        st.success(f"Successfully imported {len(df)} transactions.")

    base_df = st.session_state.base_df
    version = st.session_state.editor_version
    category_options = list(categories) + [PENDING]


    # ========================================================
    # TRANSACTION EDITOR
    # ========================================================

    st.header("✏️ Your Transactions")

    st.caption(
        "Pick a category from the **Category** dropdown, or type in the "
        "**New category** box next to it and press Enter. Typing an existing "
        "name (any capitalisation) uses that category; a new name creates it."
    )

    TYPED = "New category"

    column_config = {
        "Category": st.column_config.SelectboxColumn(
            "Category",
            options=category_options,
            required=True,
            width="medium",
        ),
        TYPED: st.column_config.TextColumn(
            "✏️ New category",
            width="medium",
            help="Type any category here. It replaces the dropdown choice.",
        ),
        "Amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
    }

    if "Date" in base_df.columns:
        column_config["Date"] = st.column_config.DateColumn(
            "Date", format="DD MMM YYYY"
        )

    # Show the typing column right after Category.
    column_order = []
    for column in base_df.columns:
        column_order.append(column)
        if column == "Category":
            column_order.append(TYPED)

    edited_df = st.data_editor(
        base_df.assign(**{TYPED: ""}),
        column_config=column_config,
        column_order=column_order,
        disabled=[c for c in base_df.columns if c != "Category"],
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        key=f"transactions_{version}",
    )


    # --------------------------------------------------------
    # TYPED CATEGORIES
    # --------------------------------------------------------
    #
    # "groceries" -> "Groceries" (existing category)
    # "soda"      -> new category "soda", counted as Spending

    lookup = {name.lower(): name for name in categories}
    lookup[PENDING.lower()] = PENDING

    typed = edited_df[TYPED].fillna("").astype(str).map(lambda s: " ".join(s.split()))
    edited_df = edited_df.drop(columns=[TYPED])

    if typed.ne("").any():

        new_categories = []

        for row, name in typed[typed.ne("")].items():

            if name.lower() not in lookup:
                categories[name] = "Spending"
                lookup[name.lower()] = name
                new_categories.append(name)

            edited_df.loc[row, "Category"] = lookup[name.lower()]

        persist()

        # Redraw so the dropdown shows the typed category
        # and the typing box is empty again.
        commit(
            edited_df,
            f"New category added: {', '.join(new_categories)}"
            if new_categories else None,
        )


    # --------------------------------------------------------
    # REMEMBER CHOICES
    # --------------------------------------------------------

    # Compared with the statement as uploaded (or as last remembered),
    # so changes still count after the table refreshes.
    changed = edited_df[
        edited_df["Category"] != st.session_state.remembered
    ]

    remember_col, info_col = st.columns([1, 3])

    with remember_col:

        if st.button(
            f"💾 Remember {len(changed)} change(s) for next time",
            disabled=changed.empty,
            help=(
                "Saves each merchant you re-categorized, so the same "
                "merchant gets your category automatically on your "
                "next statement."
            ),
        ):
            new_rules = {
                merchant_key(row["Description"]): row["Category"]
                for _, row in changed.iterrows()
                if merchant_key(row["Description"])
                and row["Category"] != PENDING
            }
            add_rules(settings, new_rules)
            persist()
            st.session_state.remembered = edited_df["Category"].copy()
            commit(edited_df, f"Remembered {len(new_rules)} merchant(s).")

    with info_col:
        if not changed.empty:
            st.caption(
                "Your edits already count in the tracker below. "
                "Remembering them just applies them to future statements too."
            )


    # --------------------------------------------------------
    # CHANGE MANY AT ONCE
    # --------------------------------------------------------

    with st.expander("⚡ Change many transactions at once"):

        merchant_counts = (
            edited_df["Description"].fillna("").value_counts()
        )

        filter_col, merchant_col = st.columns(2)

        with filter_col:
            only_in = st.selectbox(
                "Show merchants currently in",
                ["All categories"] + category_options,
                index=(len(category_options)),  # starts on Needs Categorization
            )

        if only_in != "All categories":
            visible = edited_df.loc[
                edited_df["Category"] == only_in, "Description"
            ].fillna("").unique()
            merchant_counts = merchant_counts[merchant_counts.index.isin(visible)]

        with merchant_col:
            chosen = st.multiselect(
                "Merchants",
                options=list(merchant_counts.index),
                format_func=lambda m: f"{m or '(no description)'}  ·  {merchant_counts[m]}×",
            )

        target_col, remember_box_col = st.columns(2)

        with target_col:
            target = st.selectbox(
                "Move them to (pick or type a new one)",
                list(categories),
                accept_new_options=True,
            )

        with remember_box_col:
            st.write("")
            remember_bulk = st.checkbox("Remember for next time", value=True)

        if st.button("Apply", type="primary", disabled=not (chosen and target)):

            target = " ".join(str(target).split())
            target = lookup.get(target.lower(), target)

            if target not in categories and target != PENDING:
                categories[target] = "Spending"

            persist()

            df = edited_df.copy()
            mask = df["Description"].fillna("").isin(chosen)
            df.loc[mask, "Category"] = target

            if remember_bulk:
                add_rules(settings, {m: target for m in chosen if merchant_key(m)})
                persist()

            commit(df, f"Moved {int(mask.sum())} transaction(s) to {target}.")


    # ========================================================
    # CALCULATE METRICS
    # ========================================================

    income = total_income(edited_df, categories)
    expenses = total_expenses(edited_df, categories)
    savings = total_savings(edited_df, categories)
    pending = pending_transactions(edited_df)

    savings_rate = (savings / income) * 100 if income > 0 else 0


    # ========================================================
    # OVERVIEW
    # ========================================================

    st.header("📊 Overview")

    if not pending.empty:
        st.info(
            f"{len(pending)} transaction(s) worth "
            f"₹{pending['Amount'].sum():,.2f} still need a category. "
            f"They aren't counted anywhere until you pick one."
        )
    else:
        st.success("Every transaction has a category.")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Income", f"₹{income:,.2f}")
    col2.metric("Actual Spending", f"₹{expenses:,.2f}")
    col3.metric("Savings", f"₹{savings:,.2f}")
    col4.metric("Savings Rate", f"{savings_rate:.1f}%")
    col5.metric("Needs Review", f"₹{pending['Amount'].sum():,.2f}")


    # ========================================================
    # EVERY CATEGORY
    # ========================================================

    st.header("🏷️ Category Tracker")

    st.dataframe(
        category_summary(edited_df, categories),
        column_config={
            "Money Out": st.column_config.NumberColumn(format="₹%.2f"),
            "Money In": st.column_config.NumberColumn(format="₹%.2f"),
        },
        hide_index=True,
        width="stretch",
    )


    # ========================================================
    # MONTHLY EXPENSES
    # ========================================================

    st.header("📅 Monthly Expenses")

    monthly = monthly_expenses(edited_df, categories)

    if monthly.empty:
        st.info("No spending categorized yet.")

    else:
        fig = px.bar(
            monthly,
            x="Month",
            y="Amount",
            title="Monthly Spending",
            labels={"Amount": "Spending (₹)"},
        )
        st.plotly_chart(fig, width="stretch")


    # ========================================================
    # CATEGORY BREAKDOWN
    # ========================================================

    st.header("🥧 Spending by Category")

    by_category = category_expenses(edited_df, categories)

    if by_category.empty:
        st.info("No spending categorized yet.")

    else:
        spending_rows = edited_df[
            edited_df["Category"].isin(by_category["Category"])
        ]

        if "Date" in spending_rows.columns and spending_rows["Date"].notna().any():
            first = pd.to_datetime(spending_rows["Date"]).min()
            last = pd.to_datetime(spending_rows["Date"]).max()
            if first.date() == last.date():
                period = f"{first.day} {first:%b %Y}"
            elif first.year == last.year:
                period = f"{first.day} {first:%b} – {last.day} {last:%b %Y}"
            else:
                period = f"{first.day} {first:%b %Y} – {last.day} {last:%b %Y}"
        else:
            period = "Your spending"

        show_donut(
            by_category,
            title=period,
            subtitle=(
                f"{len(spending_rows)} transactions · "
                f"{len(by_category)} categories"
            ),
        )


    # ========================================================
    # MONTHLY CATEGORY BREAKDOWN
    # ========================================================

    st.header("📈 Monthly Category Breakdown")

    monthly_category = monthly_category_expenses(edited_df, categories)

    if not monthly_category.empty:
        fig = px.bar(
            monthly_category,
            x="Month",
            y="Amount",
            color="Category",
            title="Monthly Spending by Category",
        )
        st.plotly_chart(fig, width="stretch")


    # ========================================================
    # EXPORT
    # ========================================================

    st.header("📥 Export")

    st.download_button(
        label="Download Categorized Transactions",
        data=edited_df.to_csv(index=False).encode("utf-8"),
        file_name="categorized_transactions.csv",
        mime="text/csv",
    )

    st.caption(
        "Upload this CSV again later to continue exactly where you left off."
    )


else:

    # ========================================================
    # BEFORE UPLOAD
    # ========================================================

    st.info("Upload a bank statement above to begin, or try it out first.")

    if st.button("👀 Try it with sample data", type="primary"):
        st.session_state.use_sample = True
        st.rerun()

    st.markdown(
        """
        ### How it works

        **1. Upload** your bank statement.

        **2. Automatic first guess** — food, groceries, transport, etc.
        are filled in for you, plus any merchants you told the app to remember.

        **3. You decide** — change the category of *any* transaction,
        or move many at once.

        **4. Your own categories** — add, rename or delete categories in the
        sidebar and choose whether each one counts as Spending, Income or
        Not counted.

        **5. Dashboard** — income, spending, savings and charts all follow
        your categories.
        """
    )


# ============================================================
# SIDEBAR: MANAGE CATEGORIES
# ============================================================
#
# This is written after the main page so it can use your current
# edits (edited_df). Streamlit still shows it in the sidebar.

def update_transactions(transform, message):
    """Apply a change to the current transactions (if any) and redraw."""

    if edited_df is not None:
        commit(transform(edited_df.copy()), message)
    else:
        commit(None, message)


with st.sidebar:

    st.header("🏷️ Your Categories")

    st.caption(
        "Add a row to create a category, select a row and press Delete "
        "to remove one, and choose how each one counts. To rename one "
        "without losing its transactions, use **Rename** below."
    )

    version = st.session_state.editor_version

    category_table = st.data_editor(
        pd.DataFrame({
            "Category": list(categories),
            "Counts as": list(categories.values()),
        }),
        column_config={
            "Category": st.column_config.TextColumn("Category", required=True),
            "Counts as": st.column_config.SelectboxColumn(
                "Counts as", options=KINDS, required=True, default="Spending"
            ),
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key=f"categories_{version}",
    )

    if st.button("Save categories", type="primary", width="stretch"):

        new_categories = {}

        for _, row in category_table.iterrows():

            name = str(row["Category"] or "").strip()

            if not name or name.lower() == "nan" or name == PENDING:
                continue

            kind = row["Counts as"] if row["Counts as"] in KINDS else "Spending"
            new_categories[name] = kind

        settings["categories"] = new_categories
        settings["rules"] = [
            r for r in settings["rules"] if r["category"] in new_categories
        ]
        persist()

        def remove_deleted(df):
            df.loc[~df["Category"].isin(new_categories), "Category"] = PENDING
            return df

        update_transactions(remove_deleted, "Categories saved.")


    # --------------------------------------------------------
    # RENAME
    # --------------------------------------------------------

    with st.expander("Rename a category"):

        old_name = st.selectbox("Category", list(categories), key="rename_old")
        new_name = st.text_input("New name", key="rename_new").strip()

        if st.button("Rename", disabled=not new_name or new_name == PENDING):

            # Renaming onto an existing category merges the two.
            settings["categories"] = {
                (new_name if name == old_name else name): kind
                for name, kind in categories.items()
                if not (name == new_name and name != old_name)
            }

            for rule in settings["rules"]:
                if rule["category"] == old_name:
                    rule["category"] = new_name

            persist()

            def rename(df):
                df.loc[df["Category"] == old_name, "Category"] = new_name
                return df

            update_transactions(rename, f"Renamed {old_name} → {new_name}.")


    # --------------------------------------------------------
    # REMEMBERED MERCHANTS
    # --------------------------------------------------------

    st.header("🧠 Remembered Merchants")

    st.caption(
        "Any transaction whose description contains the text gets that "
        "category. You can add your own keywords here too (e.g. `mess`)."
    )

    rules_table = st.data_editor(
        pd.DataFrame(
            settings["rules"] or [], columns=["keyword", "category"]
        ).rename(columns={"keyword": "Description contains", "category": "Category"}),
        column_config={
            "Description contains": st.column_config.TextColumn(required=True),
            "Category": st.column_config.SelectboxColumn(
                options=list(categories), required=True
            ),
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key=f"rules_{version}",
    )

    save_col, apply_col = st.columns(2)

    with save_col:
        if st.button("Save", width="stretch", key="save_rules"):
            settings["rules"] = []
            add_rules(settings, {
                str(row["Description contains"]): row["Category"]
                for _, row in rules_table.iterrows()
                if pd.notna(row["Description contains"])
                and row["Category"] in categories
            })
            persist()
            update_transactions(lambda df: df, "Remembered merchants saved.")

    with apply_col:
        if st.button(
            "Apply now",
            width="stretch",
            disabled=edited_df is None,
            help="Re-apply all remembered merchants to this statement.",
        ):
            update_transactions(
                lambda df: apply_rules(df, settings["rules"], categories),
                "Remembered merchants applied.",
            )


    # --------------------------------------------------------
    # BACKUP / RESTORE
    # --------------------------------------------------------

    st.header("💾 Backup")

    if saves_to_disk():
        st.caption(
            "Your categories are saved on this computer automatically. "
            "A backup file lets you move them to another device."
        )
    else:
        st.caption(
            "On the website your categories last for this visit only. "
            "Download a backup before you leave, and restore it next time."
        )

    st.download_button(
        "⬇️ Download my categories",
        data=settings_to_json(settings).encode("utf-8"),
        file_name="tracker_settings.json",
        mime="application/json",
        width="stretch",
    )

    backup = st.file_uploader(
        "Restore a backup", type=["json"], key="restore_backup"
    )

    if backup is not None:

        backup_key = f"{backup.name}-{backup.size}"

        if st.session_state.get("restored_backup") != backup_key:

            try:
                restored = settings_from_json(backup.getvalue().decode("utf-8"))

            except (ValueError, UnicodeDecodeError) as error:
                st.error(f"Couldn't restore that file: {error}")

            else:
                st.session_state.restored_backup = backup_key
                st.session_state.settings = restored
                settings = restored
                categories = restored["categories"]
                save_settings(restored)

                def keep_current(df):
                    # Categories used on this statement but missing
                    # from the backup are kept, not wiped.
                    for name in df["Category"].unique():
                        if name != PENDING and name not in categories:
                            categories[name] = "Spending"
                    save_settings(restored)
                    return df

                update_transactions(keep_current, "Backup restored.")
