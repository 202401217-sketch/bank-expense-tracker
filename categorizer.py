import re


# ============================================================
# KEYWORD CATEGORIES
# ============================================================

CATEGORY_RULES = {

    "Food & Dining": [
        "zomato",
        "swiggy",
        "dominos",
        "pizza hut",
        "mcdonald",
        "kfc",
        "burger king",
        "subway",
        "starbucks",
        "restaurant",
        "cafe",
        "food",
        "dining",
        "bakery",
        "shawarma",
        "omlet",
        "parathe",
        "icecream",
    ],

    "Groceries": [
        "blinkit",
        "zepto",
        "instamart",
        "bigbasket",
        "dmart",
        "groceries",
        "supermarket",
        "grocery",
    ],

    "Transport": [
        "uber",
        "ola",
        "rapido",
        "metro",
        "irctc",
        "railway",
        "indigo",
        "air india",
        "spicejet",
        "flight",
        "petrol",
        "fuel",
        "hpcl",
        "bpcl",
        "iocl",
        "parking",
        "toll",
        "transport",
        "bus",
    ],

    "Shopping": [
        "amazon",
        "flipkart",
        "myntra",
        "ajio",
        "meesho",
        "nykaa",
        "decathlon",
        "shopping",
        "mall",
        "retail",
    ],

    "Entertainment": [
        "netflix",
        "spotify",
        "youtube",
        "prime video",
        "hotstar",
        "disney",
        "bookmyshow",
        "pvr",
        "inox",
        "movie",
        "cinema",
        "steam",
        "playstation",
        "xbox",
    ],

    "Bills & Utilities": [
        "electricity",
        "torrent power",
        "adani electricity",
        "bescom",
        "water bill",
        "gas bill",
        "broadband",
        "internet",
        "airtel",
        "jio",
        "vodafone",
        "vi ",
        "bsnl",
        "mobile recharge",
        "recharge",
        "insurance",
    ],

    "Healthcare": [
        "hospital",
        "pharmacy",
        "medical",
        "apollo",
        "fortis",
        "medicine",
        "clinic",
        "doctor",
        "health",
        "diagnostic",
    ],

    "Education": [
        "college",
        "university",
        "udemy",
        "coursera",
        "education",
        "course",
        "tuition",
        "school",
        "books",
    ],

    "Banking & Finance": [
        "bank charge",
        "bank fee",
        "service charge",
        "gst",
        "interest",
        "atm fee",
        "annual fee",
        "mutual fund",
        "sip",
        "zerodha",
        "groww",
        "investment",
    ],
}


def clean_text(text):

    if text is None:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def categorize(description):

    text = clean_text(description)

    for category, keywords in CATEGORY_RULES.items():

        for keyword in keywords:

            if keyword.lower() in text:

                return category

    return "Other"