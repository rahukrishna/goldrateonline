# Kerala Gold Rate Application

This app tracks Kerala gold prices and provides:

- Current gold rate display (22K and 24K)
- Automatic checks at **10:00 AM** and **5:00 PM** (IST)
- Monthly history table
- Monthly trend graph
- Lowest and highest monthly prices

## Tech Stack

- Python
- Streamlit dashboard
- APScheduler for scheduled checks
- SQLite for local storage

## Setup

If `python` command is not recognized in terminal, use this full path:

```powershell
& "C:\Users\pkrahul0\AppData\Local\Programs\Python\Python314\python.exe"
```

1. Create and activate virtual environment:

```powershell
& "C:\Users\pkrahul0\AppData\Local\Programs\Python\Python314\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
& "C:\Users\pkrahul0\AppData\Local\Programs\Python\Python314\python.exe" -m pip install -r requirements.txt
```

## Run

Open two terminals in project root.

1. Start scheduler (captures at 10 AM and 5 PM IST):

```powershell
& "C:\Users\pkrahul0\AppData\Local\Programs\Python\Python314\python.exe" scheduler.py
```

2. Start dashboard:

```powershell
& "C:\Users\pkrahul0\AppData\Local\Programs\Python\Python314\python.exe" -m streamlit run app.py
```

## Notes

- Source page used for rates: `https://www.goodreturns.in/gold-rates/kerala.html`
- If source HTML changes, parsing rules in `gold_rate_service.py` may need an update.
- You can add manual rates from dashboard as fallback.

## Publish To GitHub

Run these commands from project root:

```powershell
git add .
git commit -m "Initial gold rate tracker app"
git push origin main
```

If your default branch is `master`, use:

```powershell
git push origin master
```

## Host Publicly (Recommended: Streamlit Community Cloud)

1. Push this repository to GitHub.
2. Go to `https://share.streamlit.io/` and sign in with GitHub.
3. Click **Create app**.
4. Select repo: `rahukrishna/goldrateonline`.
5. Set main file path: `app.py`.
6. Deploy.

Your app will get a public URL and be accessible from anywhere.

## Important Hosted Behavior

- In hosted mode, the app still fetches the latest rate whenever page loads/refreshes.
- The background scheduler (`scheduler.py`) is for always-on local/server process and usually does not run as a background service on free web app hosting.
- Use the in-app **FETCH LAST 30 DAYS** button to backfill historical data.

## Alternative Hosting (Render/Railway)

This repo includes:

- `Procfile`
- `runtime.txt`

So you can also deploy on platforms like Render or Railway.
