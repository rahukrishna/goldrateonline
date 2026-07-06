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

## Why You See "App has gone to sleep"

On Streamlit Community Cloud, sleeping after inactivity is platform behavior.
This cannot be fully disabled from app code.

If you need the app available all the time, deploy on an always-on paid host.

## Important Hosted Behavior

- In hosted mode, the app still fetches the latest rate whenever page loads/refreshes.
- The background scheduler (`scheduler.py`) is for always-on local/server process and usually does not run as a background service on free web app hosting.
- Use the in-app **FETCH LAST 30 DAYS** button to backfill historical data.

## Persistent Hosted Database (Recommended)

To keep records permanently on the internet, use PostgreSQL (for example Supabase).

### 1. Create PostgreSQL DB

- Create a project in Supabase (or any hosted Postgres).
- Copy the connection string (URI), example:

```text
postgresql://USER:PASSWORD@HOST:5432/postgres
```

### 2. Add DB URL to Streamlit Cloud

In Streamlit app settings, open **Secrets** and add:

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/postgres"
```

### 3. Redeploy / Reboot app

- Reboot app from Streamlit Cloud **Manage app**.
- On startup, app auto-creates table and uses Postgres instead of local SQLite.

### Notes

- If `DATABASE_URL` is missing, app falls back to local `gold_rates.db`.
- App automatically ensures recent 30-day history is available on startup.

## Alternative Hosting (Render/Railway)

This repo includes:

- `Procfile`
- `runtime.txt`
- `render.yaml`

So you can also deploy on platforms like Render or Railway.

## Always-On Deployment (Render Blueprint)

Use this when you want your app live all the time without the Streamlit sleep screen.

1. Push latest code to GitHub.
2. In Render, click **New** -> **Blueprint**.
3. Select this repository.
4. Render reads `render.yaml` and creates:
	 - one always-on web service (Streamlit UI)
	 - two cron jobs (10:00 AM and 5:00 PM IST captures)
5. In Render dashboard, set `DATABASE_URL` for all created services.
6. Deploy.

Notes:

- Use a paid plan (`starter` or higher) to avoid sleeping.
- Cron schedules in `render.yaml` are UTC and already mapped to IST:
	- `30 4 * * *` -> 10:00 AM IST
	- `30 11 * * *` -> 5:00 PM IST

## Automatic 10 AM / 5 PM Updates (GitHub Actions)

This repo includes a scheduler workflow at `.github/workflows/gold-rate-scheduler.yml`.

It runs automatically at:

- 10:00 AM IST
- 5:00 PM IST

### One-time setup

1. Open GitHub repo settings:
	- `https://github.com/rahukrishna/goldrateonline/settings/secrets/actions`
2. Add repository secret:

```text
Name: DATABASE_URL
Value: your Supabase/Postgres connection URI
```

3. Open Actions tab and enable workflows if prompted.

### Manual run

1. Go to GitHub Actions -> `Gold Rate Scheduler`
2. Click **Run workflow**
3. Choose slot: `AUTO`, `MORNING`, or `EVENING`

### Notes

- Workflow uses `capture_once.py` to store one snapshot per run.
- If both Streamlit and Actions use the same `DATABASE_URL`, your hosted app always shows the latest scheduled values.
