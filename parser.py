import pandas as pd
import pdfplumber
import re
from datetime import datetime

from categorizer import categorize


# ============================================================
# SETTINGS
# ============================================================

STATEMENT_YEAR = 2026


# ============================================================
# PATTERNS
# ============================================================

# Your PDF extracts transactions like:
#
# 14 Sep Paid to Samyak Enterprises
# 14 Sep Received from Tanishk Dhawan
# 31 Aug Money sent to Dhaval Natwarbhai
#
DATE_TRANSACTION_PATTERN = re.compile(
    r"^\s*(\d{1,2}\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))"
    r"\s+"
    r"(Paid to|Received from|Money sent to|"
    r"Money added to UPI Lite|Automatic payment for)"
    r"(?:\s+(.*))?$",
    re.IGNORECASE
)


# Amounts such as:
#
# - Rs.289
# + Rs.30,000
# UPI Lite - Rs.104
#
AMOUNT_PATTERN = re.compile(
    r"([+-])\s*Rs\.?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE
)


# Sometimes UPI Lite transactions do not have
# a +/- sign in the PDF text.
UPI_LITE_AMOUNT_PATTERN = re.compile(
    r"UPI Lite\s*-\s*Rs\.?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE
)


TIME_PATTERN = re.compile(
    r"^\d{1,2}:\d{2}\s*(?:AM|PM)$",
    re.IGNORECASE
)


# ============================================================
# DATE
# ============================================================

def parse_date(date_text):

    try:

        return datetime.strptime(
            f"{date_text} {STATEMENT_YEAR}",
            "%d %b %Y"
        )

    except ValueError:

        return None


# ============================================================
# AMOUNT
# ============================================================

def extract_amount(block):

    # First look for normal +/- amounts.
    matches = AMOUNT_PATTERN.findall(block)

    if matches:

        sign, value = matches[-1]

        amount = float(
            value.replace(",", "")
        )

        if sign == "+":

            return amount, "Income"

        return amount, "Expense"


    # UPI Lite transactions sometimes appear as:
    #
    # UPI Lite - Rs.104
    #
    lite_match = UPI_LITE_AMOUNT_PATTERN.search(
        block
    )

    if lite_match:

        amount = float(
            lite_match.group(1)
            .replace(",", "")
        )

        return amount, "Expense"


    # Money added to UPI Lite is a self transfer.
    #
    # Example:
    # Money added to UPI Lite
    # ...
    # Rs.684
    #
    # Find a standalone Rs amount.
    if "Money added to UPI Lite" in block:

        amounts = re.findall(
            r"Rs\.?\s*([\d,]+(?:\.\d+)?)",
            block,
            re.IGNORECASE
        )

        if amounts:

            amount = float(
                amounts[-1].replace(",", "")
            )

            return amount, "Self Transfer"


    return None, None


# ============================================================
# TAG
# ============================================================

def extract_tag(block):

    """
    Extract Paytm's transaction tag.

    Handles formats such as:

        # Money Transfer
        # Money Transfer 85
        # Money Received
        # Money Received 85
        #✈️ Travel
        #✈️ Travel 85
        # Groceries
        # Food
        # Miscellaneous
        # Self-Transfer
    """

    known_tags = [
        "Money Transfer",
        "Money Received",
        "Self-Transfer",
        "Groceries",
        "Miscellaneous",
        "Entertainment",
        "Shopping",
        "Food",
        "Travel",
    ]

    for tag in known_tags:

        pattern = (
            r"#\s*(?:✈️\s*)?"
            + re.escape(tag)
            + r"(?:\s+\d+)?"
            r"(?=\s|$)"
        )

        match = re.search(
            pattern,
            block,
            re.IGNORECASE
        )

        if match:

            return tag

    return ""
    

    lines = block.splitlines()

    for line in lines:

        line = line.strip()

        if "#" not in line:

            continue

        # Find the # symbol
        hash_position = line.find("#")

        tag = line[
            hash_position + 1:
        ].strip()

        # Remove travel emoji
        tag = tag.replace(
            "✈️",
            ""
        ).strip()

        tag = tag.replace(
            "✈",
            ""
        ).strip()

        # Remove accidental metadata
        tag = re.split(
            r"(?:UPI Lite|ICICI Bank|Rs\.|\+|-)",
            tag,
            flags=re.IGNORECASE
        )[0].strip()

        if tag:

            return tag

    return ""


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(
    first_line,
    following_lines
):

    """
    Extract description from the action line.

    Example:

    14 Sep Paid to Samyak Enterprises

    → Samyak Enterprises
    """

    match = DATE_TRANSACTION_PATTERN.match(
        first_line
    )

    if not match:

        return ""

    description = (
        match.group(3)
        or ""
    ).strip()


    # --------------------------------------------------------
    # Remove metadata that may appear on the same line
    # --------------------------------------------------------

    description = re.split(
        r"\b(?:UPI ID:|UPI Ref No:|Note:|Tag:|ICICI Bank|UPI Lite)",
        description,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()


    # Remove amount if it somehow appears
    description = re.sub(
        r"[+-]\s*Rs\.?\s*[\d,]+(?:\.\d+)?",
        "",
        description,
        flags=re.IGNORECASE
    ).strip()


    # --------------------------------------------------------
    # Add continuation lines.
    #
    # Example:
    #
    # Paid to Gujarat State Road Transport
    # Corporation
    #
    # becomes:
    #
    # Gujarat State Road Transport Corporation
    # --------------------------------------------------------

    for line in following_lines:

        line = line.strip()

        if not line:
            continue

        # Stop at metadata
        if re.match(
            r"^(UPI ID:|UPI Ref No:|Note:|Tag:|#)",
            line,
            re.IGNORECASE
        ):
            break

        if "ICICI Bank" in line:
            break

        if "UPI Lite" in line:
            break

        if AMOUNT_PATTERN.search(line):
            break

        if UPI_LITE_AMOUNT_PATTERN.search(line):
            break

        if TIME_PATTERN.match(line):
            continue

        if DATE_TRANSACTION_PATTERN.match(line):
            break

        # Ignore obvious metadata fragments
        if line.lower() == "on":
            continue

        if line.isdigit():
            continue

        description += " " + line

    # --------------------------------------------------------
    # Final cleanup
    # --------------------------------------------------------

    description = re.sub(
        r"\s+",
        " ",
        description
    ).strip()

    return description


# ============================================================
# CATEGORY
# ============================================================

def category_from_tag(
    tag,
    description
):

    tag_lower = (
        str(tag)
        .lower()
        .strip()
    )

    # Paytm's own categories
    mapping = {

        "food":
            "Food & Dining",

        "groceries":
            "Groceries",

        "travel":
            "Transport",

        "shopping":
            "Shopping",

        "entertainment":
            "Entertainment",

        "money transfer":
            "Needs Categorization",

        "money received":
            "Money Received",

        "self-transfer":
            "Self Transfer",

        "miscellaneous":
            "Other",
    }

    if tag_lower in mapping:

        return mapping[tag_lower]

    # If Paytm doesn't have a useful tag,
    # use our keyword categorizer.
    return categorize(
        description
    )


# ============================================================
# PARSE PAYTM PDF
# ============================================================

def parse_paytm_pdf(file):

    transactions = []

    with pdfplumber.open(file) as pdf:

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            text = page.extract_text()

            if not text:
                continue

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]


            # ------------------------------------------------
            # Find transaction starts
            # ------------------------------------------------

            starts = []

            for index, line in enumerate(lines):

                match = DATE_TRANSACTION_PATTERN.match(
                    line
                )

                if match:

                    starts.append(index)


            # ------------------------------------------------
            # Process each transaction
            # ------------------------------------------------

            for position, start in enumerate(
                starts
            ):

                if position + 1 < len(starts):

                    end = starts[
                        position + 1
                    ]

                else:

                    end = len(lines)


                block_lines = lines[
                    start:end
                ]

                if not block_lines:
                    continue


                # ------------------------------------------------
                # First line
                # ------------------------------------------------

                first_line = block_lines[0]

                date_match = (
                    DATE_TRANSACTION_PATTERN.match(
                        first_line
                    )
                )

                if not date_match:
                    continue


                date_text = date_match.group(1)

                action = (
                    date_match.group(2)
                    .lower()
                )


                # ------------------------------------------------
                # Date
                # ------------------------------------------------

                date = parse_date(
                    date_text
                )

                if date is None:
                    continue


                # ------------------------------------------------
                # Time
                # ------------------------------------------------

                time = ""

                if (
                    len(block_lines) > 1
                    and TIME_PATTERN.match(
                        block_lines[1]
                    )
                ):

                    time = block_lines[1]


                # ------------------------------------------------
                # Description
                # ------------------------------------------------

                description = extract_description(

                    first_line,

                    block_lines[1:]

                )


                # ------------------------------------------------
                # Amount
                # ------------------------------------------------

                block_text = "\n".join(
                    block_lines
                )

                amount, transaction_type = (
                    extract_amount(
                        block_text
                    )
                )

                if amount is None:
                    continue


                # ------------------------------------------------
                # Tag
                # ------------------------------------------------

                tag = extract_tag(
                    block_text
                )


                tag_lower = tag.lower().strip()


                # ------------------------------------------------
                # Category
                # ------------------------------------------------

                category = category_from_tag(

                    tag,

                    description

                )


                # =================================================
                # SPECIAL TRANSACTION TYPES
                # =================================================

                # Money Transfer
                #
                # IMPORTANT:
                # Do NOT automatically treat this as spending.
                # User must decide.
                if tag_lower == "money transfer":

                    transaction_type = (
                        "Money Transfer"
                    )

                    category = (
                        "Needs Categorization"
                    )


                # Self Transfer
                #
                # Excluded from expenses.
                elif tag_lower == "self-transfer":

                    transaction_type = (
                        "Self Transfer"
                    )

                    category = (
                        "Self Transfer"
                    )


                # Money Received
                elif tag_lower == "money received":

                    transaction_type = (
                        "Income"
                    )

                    category = (
                        "Money Received"
                    )


                # Money added to UPI Lite
                elif (
                    "money added to upi lite"
                    in action
                ):

                    transaction_type = (
                        "Self Transfer"
                    )

                    category = (
                        "Self Transfer"
                    )


                # Money that came in without a useful tag
                # is treated as money received by default.
                elif (
                    transaction_type == "Income"
                    and not tag
                ):

                    category = (
                        "Money Received"
                    )


                # ------------------------------------------------
                # Save transaction
                # ------------------------------------------------

                transactions.append({

                    "Date": date,

                    "Time": time,

                    "Description": description,

                    "Amount": amount,

                    "Type": transaction_type,

                    "Category": category,

                    "Paytm Tag": tag,

                    "Month": date.strftime(
                        "%Y-%m"
                    ),

                    "Page": page_number

                })


    return pd.DataFrame(
        transactions
    )


# ============================================================
# CSV
# ============================================================

def parse_csv(file):

    df = pd.read_csv(file)

    if is_tracker_export(df):

        return load_tracker_export(df)

    return normalize_dataframe(
        df
    )


# ============================================================
# EXCEL
# ============================================================

def parse_excel(file):

    df = pd.read_excel(file)

    if is_tracker_export(df):

        return load_tracker_export(df)

    return normalize_dataframe(
        df
    )


# ============================================================
# RE-IMPORT A FILE EXPORTED FROM THIS APP
# ============================================================
#
# Lets you download your categorized transactions, close the app,
# and upload that CSV later to continue where you left off.

TRACKER_COLUMNS = {
    "Date",
    "Description",
    "Amount",
    "Type",
    "Category",
}


def is_tracker_export(df):

    return TRACKER_COLUMNS.issubset(
        df.columns
    )


def load_tracker_export(df):

    df = df.copy()

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["Date"]
    )

    df["Amount"] = pd.to_numeric(
        df["Amount"],
        errors="coerce"
    ).fillna(0).abs()

    df["Description"] = (
        df["Description"]
        .fillna("")
        .astype(str)
    )

    df["Category"] = (
        df["Category"]
        .fillna("Needs Categorization")
        .astype(str)
    )

    for column in ["Time", "Paytm Tag"]:

        if column in df.columns:

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
            )

    df["Month"] = df["Date"].dt.strftime(
        "%Y-%m"
    )

    df.attrs["tracker_export"] = True

    return df.reset_index(
        drop=True
    )


# ============================================================
# GENERIC CSV / EXCEL NORMALIZER
# ============================================================

def normalize_dataframe(df):

    df = df.copy()

    column_map = {}

    for column in df.columns:

        name = str(
            column
        ).lower().strip()


        if "date" in name:

            column_map[column] = (
                "Date"
            )


        elif (
            "description" in name
            or "narration" in name
            or "particular" in name
            or "remarks" in name
            or "transaction details" in name
        ):

            column_map[column] = (
                "Description"
            )


        elif "debit" in name:

            column_map[column] = (
                "Debit"
            )


        elif "credit" in name:

            column_map[column] = (
                "Credit"
            )


        elif "amount" in name:

            column_map[column] = (
                "Amount"
            )


    df = df.rename(
        columns=column_map
    )


    if "Date" not in df.columns:

        return pd.DataFrame()


    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce",
        dayfirst=True
    )


    if "Description" not in df.columns:

        df["Description"] = ""


    df["Description"] = (
        df["Description"]
        .fillna("")
        .astype(str)
    )


    # --------------------------------------------------------
    # Debit / Credit
    # --------------------------------------------------------

    if (
        "Debit" in df.columns
        or "Credit" in df.columns
    ):

        if "Debit" not in df.columns:
            df["Debit"] = 0

        if "Credit" not in df.columns:
            df["Credit"] = 0


        df["Debit"] = pd.to_numeric(
            df["Debit"],
            errors="coerce"
        ).fillna(0)


        df["Credit"] = pd.to_numeric(
            df["Credit"],
            errors="coerce"
        ).fillna(0)


        df["Amount"] = df["Debit"]

        df["Type"] = "Expense"


        credit_mask = (
            df["Credit"] > 0
        )


        df.loc[
            credit_mask,
            "Amount"
        ] = df.loc[
            credit_mask,
            "Credit"
        ]


        df.loc[
            credit_mask,
            "Type"
        ] = "Income"


    # --------------------------------------------------------
    # Single Amount column
    # --------------------------------------------------------

    elif "Amount" in df.columns:

        df["Amount"] = (
            df["Amount"]
            .astype(str)
            .str.replace(
                ",",
                "",
                regex=False
            )
            .str.replace(
                "₹",
                "",
                regex=False
            )
            .str.replace(
                "Rs.",
                "",
                regex=False
            )
            .str.strip()
        )


        df["Amount"] = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).fillna(0)


        df["Type"] = df[
            "Amount"
        ].apply(

            lambda x:
                "Income"
                if x > 0
                else "Expense"

        )


        df["Amount"] = (
            df["Amount"]
            .abs()
        )


    else:

        return pd.DataFrame()


    df = df.dropna(
        subset=["Date"]
    )


    df = df[
        df["Amount"] > 0
    ]


    df["Category"] = df[
        "Description"
    ].apply(
        categorize
    )


    # Credits are money received unless you change them.
    df.loc[
        df["Type"] == "Income",
        "Category"
    ] = "Money Received"


    df["Month"] = df[
        "Date"
    ].dt.strftime(
        "%Y-%m"
    )


    return df[
        [
            "Date",
            "Description",
            "Amount",
            "Type",
            "Category",
            "Month"
        ]
    ]


# ============================================================
# MAIN FUNCTION
# ============================================================

def parse_statement(file):

    filename = file.name.lower()


    if filename.endswith(".pdf"):

        return parse_paytm_pdf(file)


    elif filename.endswith(".csv"):

        return parse_csv(file)


    elif filename.endswith(".xlsx"):

        return parse_excel(file)


    elif filename.endswith(".xls"):

        return parse_excel(file)


    else:

        raise ValueError(
            "Unsupported file type"
        )