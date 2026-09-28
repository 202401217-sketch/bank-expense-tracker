# Putting the tracker online (about 15 minutes, free)

You need a GitHub account and this folder. No terminal is needed; everything happens in the browser.

## 1. Put the code on GitHub

1. Go to **github.com** and sign in.
2. Click **+** (top right), then **New repository**.
   - Name: `bank-expense-tracker`
   - Choose **Public**, so recruiters can see the code.
   - Leave "Add a README" **unticked**, because this folder already has one.
   - Click **Create repository**.
3. On the empty repo page, click **uploading an existing file**.
4. Open the unzipped `bank-expense-tracker` folder, select **everything inside it** (including `.streamlit`, `.gitignore`, `docs` and `sample_data`) and drag it onto the page.
   - ⚠️ Do **not** upload `venv`, `tracker_settings.json`, or any of your real statements or exported CSVs.
   - If Windows hides `.streamlit` or `.gitignore`, turn on **View → Show → Hidden items** in File Explorer.
5. Click **Commit changes**.

## 2. Turn it into a website

1. Go to **share.streamlit.io** and sign in **with GitHub**.
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `YOUR-USERNAME/bank-expense-tracker`
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: pick something short, e.g. `sukun-expense-tracker`
4. Open **Advanced settings** and choose **Python 3.12**.
5. Click **Deploy**. The first start takes a few minutes while it installs everything.

You now have a link like `https://sukun-expense-tracker.streamlit.app`.

## 3. Finish the README

On GitHub, open `README.md`, click the ✏️ pencil, and replace:
- `https://YOUR-APP-NAME.streamlit.app` with your real link
- `YOUR-USERNAME` with your GitHub username

Then click **Commit changes**. The website updates automatically within a minute whenever you change files on GitHub.

## 4. Use it like an app on your phone

- **Android (Chrome):** open your link, tap **⋮**, then **Add to Home screen**.
- **iPhone (Safari):** open your link, tap **Share**, then **Add to Home Screen**.

It gets an icon on your home screen and opens like an app.

## Good to know

- **Your categories on the website:** each visit starts fresh (so strangers never see your categories). Use **Sidebar → 💾 Backup → Download my categories** before leaving, and **Restore a backup** next time.
- **Sleeping:** free apps go to sleep after a few days without visitors. Anyone opening the link sees a "wake up" button, and it's back in about 30 seconds.
- **Your statements:** they're only read in memory and never stored. Still, only upload your own statements.
