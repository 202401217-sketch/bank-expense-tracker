# 💰 Bank Expense Tracker

Turn a bank or UPI statement into a clear picture of where your money goes. Upload a PDF, CSV or Excel statement, fix any category with a click, and every total and chart updates as you go.

**▶ Live demo:** (https://sukun-expense-tracker.streamlit.app/), where the **Try it with sample data** button works without a statement.

![Where it went: spending by category](docs/where-it-went.png)

## Features

- **Reads real statements.** Parses Paytm UPI PDF statements plus generic bank CSV/Excel exports, including debit/credit or signed-amount columns and different column names.
- **Automatic first guess.** Uses Paytm's own tags plus keyword rules for food, groceries, transport, shopping, bills and more.
- **You have the final say.** Change the category of any transaction from a dropdown, or type a brand-new one.
- **Your own categories.** Create, rename or delete categories and choose how each counts: *Spending*, *Income* or *Not counted* (self-transfers, moving money between accounts).
- **Learns your merchants.** Remember a choice once and the same merchant is categorized automatically on your next statement.
- **Bulk edits.** Move every transaction from a merchant to a category in one step.
- **Honest totals.** Money transfers stay out of spending until you decide what they were, and refunds reduce the category they belong to.
- **Dashboard.** Income, spending, savings rate, a "where it went" donut, monthly trends and a per-category table.
- **Pick up where you left off.** Export your categorized CSV and upload it later, and back up or restore your categories as a file.

## Privacy

Statements are processed in memory to build the dashboard and are never written to disk. On the hosted site, each visitor's categories exist only for their own visit (nothing is shared between visitors) unless they download a backup.

## How the numbers work

Every transaction has a category, and every category has a type:

| Type | Counts as | Examples |
|---|---|---|
| Spending | money you spent (refunds subtract) | Food & Dining, Groceries, Hostel |
| Income | money you received | Money Received |
| Not counted | ignored | Self Transfer |

`Savings = Income − Spending`. Transactions still marked **Needs Categorization** aren't counted anywhere until you pick a category.

## Tech stack

Python · Streamlit · pandas · pdfplumber · Plotly · custom SVG chart

## Run it on your computer

```bash
git clone https://github.com/YOUR-USERNAME/bank-expense-tracker.git
cd bank-expense-tracker
python -m venv venv
venv\Scripts\activate        # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

When it runs locally, your categories are saved to `tracker_settings.json` automatically. That file is in `.gitignore`, so it never gets uploaded.

## Project structure

```
app.py              Streamlit app: upload, editor, dashboard, sidebar
parser.py           Reads Paytm PDFs and bank CSV/Excel files
categorizer.py      Keyword rules for the first automatic guess
category_store.py   Your categories, remembered merchants, backup/restore
analytics.py        Totals and breakdowns, all driven by category type
donut_chart.py      The "where it went" SVG donut card
sample_data/        A made-up statement for the demo
```

## Ideas for later

- Monthly budgets per category with alerts
- Support for more bank PDF layouts
- Sign-in with saved history across devices
