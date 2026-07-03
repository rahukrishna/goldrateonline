from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

from gold_rate_service import (
    GoldRateRecord,
    backfill_recent_days,
    ensure_recent_history,
    fetch_kerala_rates,
    init_db,
    latest_rate,
    read_rates,
    save_manual_rate,
    upsert_rate,
)

st.set_page_config(page_title="Kerala Gold Rate Tracker", layout="wide")

init_db()

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Rajdhani:wght@400;500;700&display=swap');

        :root {
            --bg1: #071a28;
            --bg2: #0b2a3d;
            --gold: #e7c978;
            --gold-strong: #d9b152;
            --card: #0f2233;
            --panel: #0c1d2b;
            --line: #264057;
            --text: #e8f2ff;
            --muted: #9ab0c3;
            --up: #6de7a9;
            --down: #ff8e93;
            --flat: #8bc8ff;
        }

        .stApp {
            background:
                radial-gradient(circle at 14% 10%, rgba(190, 152, 67, 0.18), transparent 24%),
                radial-gradient(circle at 85% 80%, rgba(44, 110, 165, 0.2), transparent 30%),
                linear-gradient(150deg, var(--bg1) 0%, var(--bg2) 60%, #0d3147 100%);
            font-family: 'Rajdhani', sans-serif;
            color: var(--text);
        }

        .block-container {
            padding-top: 0.4rem;
            padding-bottom: 2rem;
        }

        header[data-testid="stHeader"] {
            display: none;
        }

        div[data-testid="stToolbar"] {
            display: none;
        }

        .top-bar {
            background: linear-gradient(120deg, rgba(10, 28, 41, 0.95), rgba(14, 49, 68, 0.95));
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: 0 14px 34px rgba(2, 8, 15, 0.45);
            padding: 14px 18px;
            margin-bottom: 14px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-icon {
            font-size: 1.95rem;
            color: var(--gold);
            line-height: 1;
        }

        .brand-title {
            font-family: 'Cinzel', serif;
            font-size: 2rem;
            font-weight: 700;
            color: var(--gold);
            letter-spacing: 0.4px;
            line-height: 1.2;
        }

        .brand-sub {
            margin-top: 2px;
            color: #c7d9ea;
            font-size: 0.95rem;
        }

        .panel {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: linear-gradient(145deg, rgba(11, 27, 41, 0.94), rgba(13, 34, 50, 0.94));
            box-shadow: 0 12px 24px rgba(2, 7, 13, 0.4);
            padding: 12px;
            margin-bottom: 12px;
        }

        .section-title {
            color: #f2f7ff;
            font-size: 1.12rem;
            font-weight: 700;
            letter-spacing: 0.3px;
            margin: 4px 0 10px 0;
        }

        .price-card {
            border: 1px solid #30506a;
            border-radius: 12px;
            padding: 10px 12px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
            margin-bottom: 8px;
            min-height: 112px;
            background: linear-gradient(140deg, rgba(21, 40, 57, 0.95), rgba(18, 35, 51, 0.95));
        }

        .price-head {
            color: #d5e7fa;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .price-unit {
            color: var(--muted);
            font-size: 0.86rem;
            margin-bottom: 2px;
        }

        .price-value {
            font-family: 'Cinzel', serif;
            color: #ffe8a8;
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 6px;
            text-shadow: 0 0 12px rgba(232, 193, 108, 0.16);
        }

        .price-sub {
            color: #f3f8ff;
            font-size: 0.93rem;
            margin-top: 2px;
        }

        .trend-chip {
            display: inline-block;
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.84rem;
            font-weight: 700;
            border: 1px solid;
        }

        .trend-up { color: var(--up); border-color: rgba(109, 231, 169, 0.38); background: rgba(57, 185, 124, 0.16); }
        .trend-down { color: var(--down); border-color: rgba(255, 142, 147, 0.38); background: rgba(214, 66, 73, 0.16); }
        .trend-flat { color: var(--flat); border-color: rgba(139, 200, 255, 0.38); background: rgba(66, 127, 186, 0.16); }

        .status-ok {
            color: #8eeeb8;
            font-weight: 700;
            margin-top: 6px;
            font-size: 0.94rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 10px;
        }

        .stat-card {
            border: 1px solid #315069;
            border-radius: 10px;
            padding: 8px 10px;
            background: linear-gradient(145deg, rgba(15, 35, 52, 0.95), rgba(13, 28, 44, 0.95));
        }

        .stat-label {
            color: #a5bdd2;
            font-size: 0.82rem;
            margin-bottom: 1px;
        }

        .stat-value {
            color: #f4d990;
            font-family: 'Cinzel', serif;
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .stat-sub {
            color: #9db2c6;
            font-size: 0.84rem;
            margin-top: 2px;
        }

        .kpi-card {
            border: 1px solid #2d4d63;
            border-radius: 10px;
            padding: 8px 10px;
            background: linear-gradient(150deg, rgba(11, 24, 37, 0.98), rgba(8, 35, 55, 0.95));
            min-height: 84px;
        }

        .kpi-label {
            color: #c6d8e9;
            font-size: 0.82rem;
            margin-bottom: 4px;
        }

        .kpi-value {
            color: #f1d48a;
            font-family: 'Cinzel', serif;
            font-size: 1.45rem;
            line-height: 1.1;
            font-weight: 700;
        }

        .kpi-sub {
            color: #9fb4c8;
            font-size: 0.8rem;
            margin-top: 3px;
        }

        .daydelta-card {
            border: 1px solid #315069;
            border-radius: 12px;
            background: linear-gradient(145deg, rgba(15, 35, 52, 0.95), rgba(13, 28, 44, 0.95));
            padding: 10px 12px;
            min-height: 112px;
        }

        .daydelta-label {
            color: #f3f8ff;
            font-size: 0.92rem;
            font-weight: 700;
            letter-spacing: 0.2px;
            margin-bottom: 6px;
        }

        .daydelta-value {
            color: #f4d990;
            font-family: 'Cinzel', serif;
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .daydelta-chip {
            display: inline-block;
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.9rem;
            font-weight: 700;
            border: 1px solid;
        }

        .daydelta-up { color: var(--up); border-color: rgba(109, 231, 169, 0.38); background: rgba(57, 185, 124, 0.16); }
        .daydelta-down { color: var(--down); border-color: rgba(255, 142, 147, 0.38); background: rgba(214, 66, 73, 0.16); }
        .daydelta-flat { color: var(--flat); border-color: rgba(139, 200, 255, 0.38); background: rgba(66, 127, 186, 0.16); }

        .purchase-stack {
            display: grid;
            gap: 10px;
            margin-top: 6px;
            margin-bottom: 8px;
        }

        .purchase-card {
            border: 1px solid #2f526a;
            border-radius: 12px;
            padding: 12px;
            background: linear-gradient(145deg, rgba(11, 31, 48, 0.95), rgba(9, 39, 60, 0.95));
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }

        .purchase-card.buy-date {
            border-color: rgba(87, 189, 138, 0.55);
            background: linear-gradient(145deg, rgba(16, 63, 52, 0.9), rgba(12, 51, 64, 0.9));
        }

        .purchase-card.buy-slot {
            border-color: rgba(75, 139, 196, 0.55);
            background: linear-gradient(145deg, rgba(11, 44, 74, 0.92), rgba(10, 34, 61, 0.92));
        }

        .purchase-head {
            color: #d4e8fb;
            font-size: 0.84rem;
            font-weight: 700;
            letter-spacing: 0.25px;
            text-transform: uppercase;
            margin-bottom: 6px;
        }

        .purchase-main {
            color: #f5fbff;
            font-size: 1.04rem;
            font-weight: 700;
            line-height: 1.45;
        }

        .purchase-sub {
            color: #b8cce0;
            font-size: 0.9rem;
            margin-top: 6px;
            line-height: 1.35;
        }

        .purchase-badge {
            display: inline-block;
            margin-left: 8px;
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.83rem;
            font-weight: 700;
            color: #0f2437;
            background: linear-gradient(90deg, #e3c983, #f2deab);
            border: 1px solid rgba(246, 226, 168, 0.45);
        }

        .purchase-note {
            color: #9eb4c8;
            font-size: 0.84rem;
            line-height: 1.35;
        }

        .helper {
            color: #8ea6bc;
            font-size: 0.86rem;
            margin-bottom: 8px;
        }

        div[data-testid="stRadio"] label p,
        div[data-testid="stSelectbox"] label,
        div[data-testid="stNumberInput"] label,
        div[data-testid="stTextInput"] label,
        div[data-testid="stDateInput"] label,
        div[data-testid="stTimeInput"] label {
            color: #d8e7f5 !important;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #304b61;
            border-radius: 12px;
            overflow: hidden;
        }

        div[data-testid="stMetric"] {
            border: 1px solid #315069;
            border-radius: 12px;
            background: linear-gradient(145deg, rgba(15, 35, 52, 0.95), rgba(13, 28, 44, 0.95));
            padding: 10px 12px;
        }

        div[data-testid="stMetricLabel"] {
            margin-bottom: 2px;
        }

        div[data-testid="stMetricLabel"] p {
            color: #dcecff !important;
            font-weight: 700 !important;
            font-size: 1.02rem !important;
            letter-spacing: 0.2px !important;
            opacity: 1 !important;
            text-shadow: 0 1px 0 rgba(0, 0, 0, 0.25);
        }

        div[data-testid="stMetricValue"] {
            color: #f4d990 !important;
            font-family: 'Cinzel', serif !important;
            font-size: 2rem !important;
            line-height: 1.1 !important;
        }

        div[data-testid="stMetricDelta"] {
            color: #7ee7ae !important;
            font-weight: 700 !important;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 999px !important;
            border: 1px solid #d0b06a !important;
            background: linear-gradient(90deg, #c39c4e 0%, #e5ca87 50%, #c39c4e 100%) !important;
            color: #102033 !important;
            font-weight: 700 !important;
            letter-spacing: 0.4px !important;
            box-shadow: 0 6px 18px rgba(6, 11, 19, 0.35) !important;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            filter: brightness(1.04);
        }

        @media (max-width: 900px) {
            .brand-title {
                font-size: 1.5rem;
            }
            .stats-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def trend_chip(delta: Optional[float], label: str = "") -> str:
    label_prefix = f"{label}: " if label else ""
    if delta is None:
        return f'<span class="trend-chip trend-flat">{label_prefix}No previous data</span>'
    if delta > 0:
        return f'<span class="trend-chip trend-up">{label_prefix}▲ +{delta:.2f}</span>'
    if delta < 0:
        return f'<span class="trend-chip trend-down">{label_prefix}▼ {delta:.2f}</span>'
    return f'<span class="trend-chip trend-flat">{label_prefix}→ 0.00</span>'


def format_date_label(ts: pd.Timestamp) -> str:
    return ts.strftime("%d %b %Y")


def delta_text(value: float) -> str:
    if pd.isna(value):
        return "-"
    if value > 0:
        return f"▲ +{value:,.2f}"
    if value < 0:
        return f"▼ {value:,.2f}"
    return "→ 0.00"


def build_forecast(daily_df: pd.DataFrame, target_dates: pd.DatetimeIndex, value_col: str) -> pd.DataFrame:
    """
    Simple and stable forecast model:
    - linear trend over time
    - weekday seasonality from residual means
    """
    train = daily_df[["date", value_col]].dropna().copy()
    train = train.sort_values("date")

    if len(train) < 7:
        return pd.DataFrame()

    x = np.arange(len(train), dtype=float)
    y = train[value_col].astype(float).to_numpy()

    # Trend component
    slope, intercept = np.polyfit(x, y, 1)
    trend_in_sample = intercept + slope * x

    # Weekday seasonal component
    residuals = y - trend_in_sample
    seasonal_frame = pd.DataFrame(
        {
            "weekday": train["date"].dt.weekday,
            "residual": residuals,
        }
    )
    weekday_seasonality = seasonal_frame.groupby("weekday")["residual"].mean().to_dict()

    future_index = np.arange(len(train), len(train) + len(target_dates), dtype=float)
    future_trend = intercept + slope * future_index
    future_seasonal = np.array([weekday_seasonality.get(d.weekday(), 0.0) for d in target_dates])
    yhat = future_trend + future_seasonal

    resid_std = float(np.std(residuals)) if len(residuals) > 1 else 0.0

    return pd.DataFrame(
        {
            "date": target_dates,
            "yhat": yhat,
            "yhat_lower": yhat - 1.28 * resid_std,
            "yhat_upper": yhat + 1.28 * resid_std,
        }
    )


def fetch_news_sentiment() -> float:
    """
    Lightweight headline sentiment proxy for India-gold news.
    Returns value in approximately [-1, 1].
    """
    rss_url = "https://news.google.com/rss/search?q=india+gold+price&hl=en-IN&gl=IN&ceid=IN:en"
    positive_words = {
        "rise", "rises", "up", "gains", "gain", "surge", "record", "high", "strong", "bullish"
    }
    negative_words = {
        "fall", "falls", "down", "drops", "drop", "weak", "slump", "low", "bearish", "decline"
    }

    try:
        r = requests.get(rss_url, timeout=8)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = root.findall(".//item")[:25]
        if not items:
            return 0.0

        score = 0.0
        for item in items:
            title = (item.findtext("title") or "").lower()
            text = re.sub(r"[^a-z\s]", " ", title)
            words = set(text.split())
            score += len(words & positive_words)
            score -= len(words & negative_words)

        # Compress to bounded range
        return float(np.tanh(score / 10.0))
    except Exception:
        return 0.0


def fetch_market_factors(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """
    Pulls macro signals:
    - Global gold futures close (GC=F)
    - USDINR fx close (INR=X)
    """
    if yf is None:
        return pd.DataFrame(columns=["date", "gold_usd", "usd_inr"])

    try:
        start = start_date.strftime("%Y-%m-%d")
        end = (end_date + pd.Timedelta(days=3)).strftime("%Y-%m-%d")

        gold = yf.download("GC=F", start=start, end=end, auto_adjust=True, progress=False)
        fx = yf.download("INR=X", start=start, end=end, auto_adjust=True, progress=False)

        if gold.empty or fx.empty:
            return pd.DataFrame(columns=["date", "gold_usd", "usd_inr"])

        factors = pd.DataFrame(
            {
                "date": pd.to_datetime(gold.index).tz_localize(None).floor("D"),
                "gold_usd": gold["Close"].astype(float).to_numpy(),
            }
        )
        fx_df = pd.DataFrame(
            {
                "date": pd.to_datetime(fx.index).tz_localize(None).floor("D"),
                "usd_inr": fx["Close"].astype(float).to_numpy(),
            }
        )

        merged = factors.merge(fx_df, on="date", how="outer").sort_values("date")
        merged[["gold_usd", "usd_inr"]] = merged[["gold_usd", "usd_inr"]].ffill().bfill()
        return merged.dropna()
    except Exception:
        return pd.DataFrame(columns=["date", "gold_usd", "usd_inr"])


def build_enhanced_forecast(
    daily_df: pd.DataFrame,
    target_dates: pd.DatetimeIndex,
    value_col: str,
) -> tuple[pd.DataFrame, str]:
    """
    Enhanced model:
    - autoregressive lags
    - weekday seasonality
    - optional macro regressors (gold_usd, usd_inr)
    - live news sentiment adjustment
    Falls back to baseline model when factors are unavailable.
    """
    train = daily_df[["date", value_col]].dropna().sort_values("date").copy()
    if len(train) < 20:
        return build_forecast(daily_df, target_dates, value_col), "baseline"

    factors = fetch_market_factors(train["date"].min(), max(train["date"].max(), target_dates.max()))
    if not factors.empty:
        train = train.merge(factors, on="date", how="left")

    train["lag1"] = train[value_col].shift(1)
    train["lag2"] = train[value_col].shift(2)
    train["lag7"] = train[value_col].shift(7)
    train["roll7"] = train[value_col].rolling(7).mean().shift(1)
    train["dow_sin"] = np.sin(2 * np.pi * train["date"].dt.weekday / 7)
    train["dow_cos"] = np.cos(2 * np.pi * train["date"].dt.weekday / 7)

    feature_cols = ["lag1", "lag2", "lag7", "roll7", "dow_sin", "dow_cos"]
    if "gold_usd" in train.columns and "usd_inr" in train.columns:
        feature_cols.extend(["gold_usd", "usd_inr"])

    reg = train.dropna(subset=feature_cols + [value_col]).copy()
    if len(reg) < 14:
        return build_forecast(daily_df, target_dates, value_col), "baseline"

    X = reg[feature_cols].to_numpy(dtype=float)
    y = reg[value_col].to_numpy(dtype=float)

    # Linear regression via least squares
    X_aug = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X_aug, y, rcond=None)

    # Prepare future factor values
    future_factors = pd.DataFrame({"date": target_dates})
    if not factors.empty:
        future_factors = future_factors.merge(factors, on="date", how="left")
        future_factors[["gold_usd", "usd_inr"]] = future_factors[["gold_usd", "usd_inr"]].ffill().bfill()

    series = train[["date", value_col]].copy().set_index("date")[value_col]
    preds = []
    news_bias = fetch_news_sentiment()
    resid_std = float(np.std(y - (X_aug @ beta))) if len(y) > 2 else 0.0

    for d in target_dates:
        lag1 = float(series.iloc[-1])
        lag2 = float(series.iloc[-2]) if len(series) > 1 else lag1
        lag7 = float(series.iloc[-7]) if len(series) > 6 else lag1
        roll7 = float(series.tail(7).mean()) if len(series) >= 1 else lag1
        dow_sin = float(np.sin(2 * np.pi * d.weekday() / 7))
        dow_cos = float(np.cos(2 * np.pi * d.weekday() / 7))

        row = [lag1, lag2, lag7, roll7, dow_sin, dow_cos]
        if "gold_usd" in feature_cols:
            ff = future_factors[future_factors["date"] == d]
            gold_usd = float(ff["gold_usd"].iloc[0]) if not ff.empty and pd.notna(ff["gold_usd"].iloc[0]) else float(train["gold_usd"].iloc[-1])
            usd_inr = float(ff["usd_inr"].iloc[0]) if not ff.empty and pd.notna(ff["usd_inr"].iloc[0]) else float(train["usd_inr"].iloc[-1])
            row.extend([gold_usd, usd_inr])

        x_row = np.array([1.0] + row, dtype=float)
        yhat = float(x_row @ beta)

        # Small bias from live news sentiment in INR units.
        yhat += float(news_bias * 0.25 * resid_std)

        preds.append(yhat)
        series.loc[d] = yhat

    yhat_arr = np.array(preds)
    return (
        pd.DataFrame(
            {
                "date": target_dates,
                "yhat": yhat_arr,
                "yhat_lower": yhat_arr - 1.28 * resid_std,
                "yhat_upper": yhat_arr + 1.28 * resid_std,
            }
        ),
        "enhanced",
    )


def build_factor_outlook(daily_df: pd.DataFrame, value_col: str, horizon_end: pd.Timestamp) -> list[str]:
    notes: list[str] = []

    # Market factors (global gold and USD/INR)
    factors = fetch_market_factors(pd.Timestamp.now().floor("D") - pd.Timedelta(days=21), horizon_end)
    if len(factors) >= 6:
        latest = factors.iloc[-1]
        prev = factors.iloc[-6]
        gold_delta = float(latest["gold_usd"] - prev["gold_usd"])
        fx_delta = float(latest["usd_inr"] - prev["usd_inr"])

        if gold_delta > 0:
            notes.append("Global gold futures are trending up over the last week, which can push Kerala retail gold rates higher.")
        elif gold_delta < 0:
            notes.append("Global gold futures are trending down over the last week, which can ease Kerala retail gold rates.")
        else:
            notes.append("Global gold futures are mostly flat this week, giving neutral pressure on local gold rates.")

        if fx_delta > 0:
            notes.append("USD/INR is rising, making imported gold costlier in INR and adding upside pressure.")
        elif fx_delta < 0:
            notes.append("USD/INR is softening, which can reduce INR gold cost pressure.")
        else:
            notes.append("USD/INR is stable, so currency impact is currently limited.")
    else:
        notes.append("Live macro factor feed is limited right now; forecast is relying more on local price history.")

    # News sentiment proxy
    sentiment = fetch_news_sentiment()
    if sentiment > 0.2:
        notes.append("Recent India gold news flow is positive/bullish, slightly biasing short-term prices upward.")
    elif sentiment < -0.2:
        notes.append("Recent India gold news flow is negative/bearish, slightly biasing short-term prices downward.")
    else:
        notes.append("Recent India gold headlines are mixed, with limited directional signal.")

    # Weekday pattern from historical residual means
    train = daily_df[["date", value_col]].dropna().sort_values("date").copy()
    if len(train) >= 14:
        x = np.arange(len(train), dtype=float)
        y = train[value_col].astype(float).to_numpy()
        slope, intercept = np.polyfit(x, y, 1)
        residual = y - (intercept + slope * x)
        w = pd.DataFrame({"weekday": train["date"].dt.weekday, "res": residual})
        weekday_mean = w.groupby("weekday", as_index=False)["res"].mean()
        low_day = int(weekday_mean.loc[weekday_mean["res"].idxmin(), "weekday"])
        day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][low_day]
        notes.append(f"Historical weekday effect suggests comparatively softer pricing around {day_name}.")

    return notes


def recommend_buy_time(df: pd.DataFrame, value_col: str, buy_date: pd.Timestamp) -> tuple[str, str]:
    """
    Recommend MORNING vs EVENING purchase time from historical slot behavior.
    Returns (recommended_slot, explanation).
    """

    def classify_slot(row: pd.Series) -> Optional[str]:
        raw = str(row.get("slot", "")).upper()
        if "MORNING" in raw:
            return "MORNING"
        if "EVENING" in raw:
            return "EVENING"

        ts = row.get("recorded_at")
        if pd.isna(ts):
            return None
        hr = int(pd.Timestamp(ts).hour)
        if hr <= 12:
            return "MORNING"
        if hr >= 15:
            return "EVENING"
        return None

    slot_df = df[["recorded_at", "date", "slot", value_col]].dropna(subset=["recorded_at", value_col]).copy()
    if slot_df.empty:
        return "MORNING", "Insufficient slot history; defaulting to MORNING for better practical liquidity."

    slot_df["slot_class"] = slot_df.apply(classify_slot, axis=1)
    slot_df = slot_df.dropna(subset=["slot_class"])
    if slot_df.empty:
        return "MORNING", "Slot labels are unavailable; defaulting to MORNING."

    # Prefer weekday-specific comparison for the selected buy date.
    target_weekday = int(pd.Timestamp(buy_date).weekday())
    weekday_df = slot_df[slot_df["recorded_at"].dt.weekday == target_weekday].copy()

    def slot_means(data: pd.DataFrame) -> tuple[Optional[float], Optional[float], int]:
        if data.empty:
            return None, None, 0
        per_day = (
            data.groupby(["date", "slot_class"], as_index=False)[value_col]
            .mean()
            .pivot(index="date", columns="slot_class", values=value_col)
        )
        paired = per_day.dropna(subset=[c for c in ["MORNING", "EVENING"] if c in per_day.columns])

        m_val = float(data[data["slot_class"] == "MORNING"][value_col].mean()) if (data["slot_class"] == "MORNING").any() else None
        e_val = float(data[data["slot_class"] == "EVENING"][value_col].mean()) if (data["slot_class"] == "EVENING").any() else None
        return m_val, e_val, int(len(paired))

    m_wd, e_wd, n_wd = slot_means(weekday_df)
    m_all, e_all, n_all = slot_means(slot_df)

    use_weekday = n_wd >= 4 and m_wd is not None and e_wd is not None
    m_ref = m_wd if use_weekday else m_all
    e_ref = e_wd if use_weekday else e_all
    pair_count = n_wd if use_weekday else n_all

    if m_ref is None and e_ref is None:
        return "MORNING", "Not enough MORNING/EVENING history to compare; defaulting to MORNING."
    if e_ref is None:
        return "MORNING", "Historical EVENING data is limited; MORNING has stronger support in the dataset."
    if m_ref is None:
        return "EVENING", "Historical MORNING data is limited; EVENING has stronger support in the dataset."

    if m_ref <= e_ref:
        slot = "MORNING"
        diff = e_ref - m_ref
    else:
        slot = "EVENING"
        diff = m_ref - e_ref

    scope = "weekday-matched" if use_weekday else "overall"
    note = f"Based on {scope} slot history ({pair_count} paired days), {slot} is typically lower by about INR {diff:.2f}."
    return slot, note


def render_price_card(column, title: str, one_g: float, eight_g: float, delta_1g: Optional[float]) -> None:
    delta_8g = None if delta_1g is None else delta_1g * 8
    column.markdown(
        f"""
        <div class="price-card">
            <div class="price-head">{title}</div>
            <div class="price-unit">1g</div>
            <div class="price-value">INR {one_g:,.2f}</div>
            {trend_chip(delta_1g, '1g')}
            {trend_chip(delta_8g, '8g')}
            <div class="price-sub">Sovereign (8g): INR {eight_g:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, amount_value: float, date_value: str) -> str:
    return (
        '<div class="stat-card">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{amount_value:,.2f}</div>'
        f'<div class="stat-sub">({date_value})</div>'
        "</div>"
    )


def kpi_card(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        '<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f"{sub_html}"
        "</div>"
    )


def day_delta_card(label: str, amount_value: float, delta: Optional[float]) -> str:
    if delta is None or pd.isna(delta):
        delta_class = "daydelta-flat"
    elif delta > 0:
        delta_class = "daydelta-up"
    elif delta < 0:
        delta_class = "daydelta-down"
    else:
        delta_class = "daydelta-flat"

    return (
        '<div class="daydelta-card">'
        f'<div class="daydelta-label">{label}</div>'
        f'<div class="daydelta-value">INR {amount_value:,.2f}</div>'
        f'<span class="daydelta-chip {delta_class}">{delta_text(delta if delta is not None else np.nan)}</span>'
        "</div>"
    )


def render_manual_form() -> None:
    log_rows = read_rates()
    log_df = pd.DataFrame(log_rows)
    if not log_df.empty and "recorded_at" in log_df.columns:
        log_df = log_df.sort_values("recorded_at", ascending=False).head(8).copy()

    with st.form("manual_rate_form"):
        now_local = datetime.now()

        top_left, top_right = st.columns(2, gap="medium")

        with top_left:
            with st.container(border=True):
                st.caption("Record Parameters")
                entry_date = st.date_input("Date", value=now_local.date())
                entry_time = st.time_input("Time", value=now_local.replace(second=0, microsecond=0).time())
                slot_choice = st.selectbox("Slot", ["LIVE", "MORNING", "EVENING", "HISTORICAL", "CUSTOM"])

        with top_right:
            with st.container(border=True):
                st.caption("Details")
                st.radio("Gold Purity", ["22K", "24K"], horizontal=True, label_visibility="collapsed")
                auto_8g_hint = st.checkbox("Auto-calc Sovereign from 1g", value=True)
                manual_notes = st.text_area("Notes", value="Manual entry from dashboard", height=100, max_chars=180)

        custom_slot = ""
        if slot_choice == "CUSTOM":
            custom_slot = st.text_input("Custom Slot Name", placeholder="NOON_CHECK")

        p1, p2 = st.columns(2, gap="medium")
        with p1:
            rate_22k = st.number_input("22K Rate (INR)", min_value=0.0, step=1.0)
        with p2:
            rate_24k = st.number_input("24K Rate (INR)", min_value=0.0, step=1.0)

        if auto_8g_hint:
            st.caption(
                f"Preview Sovereign: 22K 8g = INR {rate_22k * 8:,.2f} | "
                f"24K 8g = INR {rate_24k * 8:,.2f}"
            )

        info_left, info_right = st.columns(2, gap="medium")
        with info_left:
            with st.container(border=True):
                st.caption("Last Entry Snapshot")
                if not log_df.empty:
                    last_entry = (
                        log_df.head(1)[["recorded_at", "slot", "rate_22k", "rate_24k"]]
                        .rename(
                            columns={
                                "recorded_at": "Recorded At",
                                "slot": "Slot",
                                "rate_22k": "22K (1g)",
                                "rate_24k": "24K (1g)",
                            }
                        )
                        .copy()
                    )
                    last_entry["22K (1g)"] = last_entry["22K (1g)"].map(lambda v: f"{float(v):,.2f}")
                    last_entry["24K (1g)"] = last_entry["24K (1g)"].map(lambda v: f"{float(v):,.2f}")
                    st.dataframe(last_entry, width="stretch", hide_index=True)
                else:
                    st.caption("No previous entries available.")

        with info_right:
            with st.container(border=True):
                st.caption("Manage Entry Log")
                if not log_df.empty:
                    manage_log = (
                        log_df[["recorded_at", "slot"]]
                        .rename(columns={"recorded_at": "Recorded At", "slot": "Slot"})
                        .copy()
                    )
                    st.dataframe(manage_log, width="stretch", hide_index=True)
                else:
                    st.caption("No log yet")

        b1, b2 = st.columns(2)
        with b1:
            submitted = st.form_submit_button("Save Manual Record", use_container_width=True)
        with b2:
            clear_pressed = st.form_submit_button("Undo", use_container_width=True)

        if clear_pressed:
            st.info("Undo button is a UI placeholder. Use Manage Entry Log actions to remove entries in a later update.")

        if submitted:
            entry_datetime = datetime.combine(entry_date, entry_time)

            if slot_choice == "CUSTOM":
                if not custom_slot.strip():
                    st.error("Please enter a custom slot name.")
                    st.stop()
                slot_value = custom_slot.strip().upper().replace(" ", "_")
            else:
                slot_value = slot_choice

            save_manual_rate(
                rate_22k=rate_22k,
                rate_24k=rate_24k,
                recorded_at=entry_datetime,
                slot=slot_value,
                notes=manual_notes.strip() or "Manual entry from dashboard",
            )
            st.success("Manual rate saved successfully.")
            st.rerun()


if hasattr(st, "dialog"):
    @st.dialog("Advanced Historical Data Entry Module")
    def open_manual_entry_dialog() -> None:
        render_manual_form()
else:
    def open_manual_entry_dialog() -> None:
        render_manual_form()


def render_manual_entry_launcher(button_key: str) -> None:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Manual Entry</div>', unsafe_allow_html=True)
    st.caption("Click to open a popup and enter/update rates in a cleaner workspace.")

    if st.button("Open Advanced Entry Popup", key=button_key, use_container_width=False):
        if hasattr(st, "dialog"):
            open_manual_entry_dialog()
        else:
            st.info("Popup is not available in this Streamlit runtime. Showing inline form instead.")
            render_manual_form()

    st.markdown('</div>', unsafe_allow_html=True)


left_header, right_actions = st.columns([3, 2])
with left_header:
    st.markdown(
        """
        <div class="top-bar">
            <div class="brand">
                <div class="brand-icon">✦</div>
                <div>
                    <div class="brand-title">Kerala Gold Rate Tracker</div>
                    <div class="brand-sub">Live rate, refresh + auto-capture (10AM and 5PM IST)</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with right_actions:
    btn_col1, btn_col2 = st.columns(2)
    fetch_pressed = btn_col1.button("FETCH LAST 30 DAYS", use_container_width=True)
    live_pressed = btn_col2.button("UPDATE LIVE", use_container_width=True)

# Keep a rolling 30-day history available automatically.
try:
    ensure_recent_history(days=30, include_today=False)
except Exception:
    # Non-blocking: app can still work with existing DB data or manual entries.
    pass

if fetch_pressed:
    with st.spinner("Fetching last 30 days history..."):
        result = backfill_recent_days(days=30, include_today=False)
    st.success(f"Backfill complete: saved {result['inserted']} days, failed {result['failed']} days.")

# Always fetch latest on app launch/refresh. Button provides explicit user intent and message.
live_status = ""
try:
    now = datetime.now()
    live_22k, live_24k = fetch_kerala_rates()
    upsert_rate(
        GoldRateRecord(
            recorded_at=now,
            slot="LIVE",
            rate_22k=live_22k,
            rate_24k=live_24k,
            notes="Live fetch on dashboard refresh",
        )
    )
    live_status = "Latest price fetched live."
    if live_pressed:
        st.success("Live update completed.")
except Exception as exc:
    st.warning(
        "Live fetch is temporarily blocked by source (common on cloud IPs). "
        "You can use Fetch Last 30 Days or add manual rates below. "
        f"Details: {exc}"
    )

latest = latest_rate()
rows = read_rates()
df = pd.DataFrame(rows)

if df.empty or not latest:
    st.warning("No data available yet. Use Update Live or add manual rates.")
    render_manual_entry_launcher(button_key="open_manual_entry_empty")
else:
    # Normalize mixed timestamp formats (with and without timezone suffix).
    raw_ts = df["recorded_at"].astype(str).str.strip()
    has_tz = raw_ts.str.contains(r"(Z|[+-]\d{2}:\d{2})$", regex=True)
    normalized_ts = raw_ts.where(has_tz, raw_ts + "+05:30")
    df["recorded_at"] = (
        pd.to_datetime(normalized_ts, errors="coerce", utc=True)
        .dt.tz_convert("Asia/Kolkata")
        .dt.tz_localize(None)
    )
    df = df.dropna(subset=["recorded_at"])
    df = df.sort_values("recorded_at")
    df["rate_22k_8g"] = df["rate_22k"] * 8
    df["rate_24k_8g"] = df["rate_24k"] * 8
    df["date"] = df["recorded_at"].dt.floor("D")

    previous = None
    if len(df) >= 2:
        previous = df.iloc[-2]

    delta_22 = None
    delta_24 = None
    if previous is not None:
        delta_22 = float(latest["rate_22k"] - previous["rate_22k"])
        delta_24 = float(latest["rate_24k"] - previous["rate_24k"])

    current_month = datetime.now().strftime("%Y-%m")
    month_df = df[df["recorded_at"].dt.strftime("%Y-%m") == current_month].copy()
    stats_source = month_df if not month_df.empty else df

    idx_low_22 = stats_source["rate_22k"].idxmin()
    idx_high_22 = stats_source["rate_22k"].idxmax()
    idx_low_24 = stats_source["rate_24k"].idxmin()
    idx_high_24 = stats_source["rate_24k"].idxmax()

    low_22_date = format_date_label(stats_source.loc[idx_low_22, "recorded_at"])
    high_22_date = format_date_label(stats_source.loc[idx_high_22, "recorded_at"])
    low_24_date = format_date_label(stats_source.loc[idx_low_24, "recorded_at"])
    high_24_date = format_date_label(stats_source.loc[idx_high_24, "recorded_at"])
    low_22_value = float(stats_source.loc[idx_low_22, "rate_22k"])
    high_22_value = float(stats_source.loc[idx_high_22, "rate_22k"])
    low_24_value = float(stats_source.loc[idx_low_24, "rate_24k"])
    high_24_value = float(stats_source.loc[idx_high_24, "rate_24k"])

    daily_rates = (
        df.groupby("date", as_index=False)[["rate_22k", "rate_24k", "rate_22k_8g", "rate_24k_8g"]]
        .mean()
        .sort_values("date")
    )
    daily_rates["d_22k_1g"] = daily_rates["rate_22k"].diff()
    daily_rates["d_24k_1g"] = daily_rates["rate_24k"].diff()
    daily_rates["d_22k_8g"] = daily_rates["rate_22k_8g"].diff()
    daily_rates["d_24k_8g"] = daily_rates["rate_24k_8g"].diff()

    latest_day_delta_22_1g = None
    latest_day_delta_24_1g = None
    latest_day_delta_22_8g = None
    latest_day_delta_24_8g = None
    if len(daily_rates) >= 2:
        latest_day_delta_22_1g = float(daily_rates.iloc[-1]["d_22k_1g"])
        latest_day_delta_24_1g = float(daily_rates.iloc[-1]["d_24k_1g"])
        latest_day_delta_22_8g = float(daily_rates.iloc[-1]["d_22k_8g"])
        latest_day_delta_24_8g = float(daily_rates.iloc[-1]["d_24k_8g"])

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    k1, k2, k3, k4, k5, k6 = st.columns(6, gap="small")
    k1.markdown(kpi_card("Current 22K", f"INR {latest['rate_22k']:,.2f}", latest["recorded_at"]), unsafe_allow_html=True)
    k2.markdown(kpi_card("Current 24K", f"INR {latest['rate_24k']:,.2f}", latest["recorded_at"]), unsafe_allow_html=True)
    k3.markdown(kpi_card("Month Lowest 22K", f"INR {low_22_value:,.2f}", low_22_date), unsafe_allow_html=True)
    k4.markdown(kpi_card("Month Highest 22K", f"INR {high_22_value:,.2f}", high_22_date), unsafe_allow_html=True)
    k5.markdown(kpi_card("Month Lowest 24K", f"INR {low_24_value:,.2f}", low_24_date), unsafe_allow_html=True)
    k6.markdown(kpi_card("Month Highest 24K", f"INR {high_24_value:,.2f}", high_24_date), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Today vs Last Day (Up/Down)</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4, gap="small")
    d1.markdown(
        day_delta_card("22K - 1g", float(daily_rates.iloc[-1]["rate_22k"]), latest_day_delta_22_1g),
        unsafe_allow_html=True,
    )
    d2.markdown(
        day_delta_card("22K - 8g", float(daily_rates.iloc[-1]["rate_22k_8g"]), latest_day_delta_22_8g),
        unsafe_allow_html=True,
    )
    d3.markdown(
        day_delta_card("24K - 1g", float(daily_rates.iloc[-1]["rate_24k"]), latest_day_delta_24_1g),
        unsafe_allow_html=True,
    )
    d4.markdown(
        day_delta_card("24K - 8g", float(daily_rates.iloc[-1]["rate_24k_8g"]), latest_day_delta_24_8g),
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if "show_forecast_graph" not in st.session_state:
        st.session_state["show_forecast_graph"] = False

    main_left, main_right = st.columns([1.4, 1.0], gap="medium")

    with main_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Historical + Trend</div>', unsafe_allow_html=True)

        hc1, hc2, hc3 = st.columns([1.15, 1.9, 1.0], gap="small")
        with hc1:
            unit_choice = st.radio("Unit", ["1g", "Sovereign"], horizontal=True, key="hist_unit")
        with hc2:
            period_choice = st.radio(
                "Range",
                ["1 Week", "1 Month", "This Month", "6 Months", "1 Year", "All"],
                horizontal=True,
                key="hist_range",
            )
        with hc3:
            forecast_type = st.radio("Type", ["22K", "24K"], horizontal=True, key="hist_type")

        toggle_label = "Hide Forecast Graph" if st.session_state["show_forecast_graph"] else "Show Forecast Graph"
        if st.button(toggle_label, key="toggle_forecast_graph", use_container_width=False):
            st.session_state["show_forecast_graph"] = not st.session_state["show_forecast_graph"]
        st.caption("Forecast graph visibility is controlled from here and shown in the right forecast panel.")

        now_ts = pd.Timestamp.now()
        if period_choice == "1 Week":
            start_ts = now_ts - pd.Timedelta(days=7)
        elif period_choice == "1 Month":
            start_ts = now_ts - pd.DateOffset(months=1)
        elif period_choice == "This Month":
            start_ts = now_ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period_choice == "6 Months":
            start_ts = now_ts - pd.DateOffset(months=6)
        elif period_choice == "1 Year":
            start_ts = now_ts - pd.DateOffset(years=1)
        else:
            start_ts = df["recorded_at"].min()

        filtered_df = df[df["recorded_at"] >= start_ts].copy()
        if filtered_df.empty:
            filtered_df = df.copy()

        if unit_choice == "1g":
            series_cols = ["rate_22k", "rate_24k"]
            series_name_map = {"rate_22k": "22K", "rate_24k": "24K"}
            y_title = "Price (INR / 1g)"
        else:
            series_cols = ["rate_22k_8g", "rate_24k_8g"]
            series_name_map = {"rate_22k_8g": "22K", "rate_24k_8g": "24K"}
            y_title = "Price (INR / 8g)"

        plot_df = filtered_df[["recorded_at", *series_cols]].melt(
            id_vars=["recorded_at"],
            value_vars=series_cols,
            var_name="type",
            value_name="price",
        )
        plot_df["type"] = plot_df["type"].map(series_name_map)

        fig = px.line(
            plot_df,
            x="recorded_at",
            y="price",
            color="type",
            markers=True,
            labels={"recorded_at": "Date", "price": y_title, "type": ""},
            color_discrete_map={"22K": "#e15d5d", "24K": "#4ba3f1"},
        )
        fig.update_traces(
            line=dict(width=3),
            marker=dict(size=7),
            hovertemplate="%{x|%Y-%m-%d}<br>%{fullData.name}: INR %{y:,.2f}<extra></extra>",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(6,14,21,0.65)",
            font=dict(color="#dbeaff"),
            legend=dict(orientation="h", y=1.08, x=0.01),
            hovermode="x unified",
            margin=dict(l=20, r=10, t=10, b=20),
            xaxis=dict(showgrid=False, linecolor="#334b5d"),
            yaxis=dict(showgrid=True, gridcolor="#253a4b", linecolor="#334b5d"),
        )

        event = st.plotly_chart(
            fig,
            width="stretch",
            on_select="rerun",
            selection_mode=("points",),
            config={"displayModeBar": True, "scrollZoom": True},
        )

        selected_points = event.get("selection", {}).get("points", []) if event else []
        if selected_points:
            p = selected_points[-1]
            selected_type = p.get("legendgroup") or p.get("curveNumber", "")
            selected_date = p.get("x", "")
            selected_price = p.get("y", "")
            st.info(f"Selected: {selected_type} on {selected_date} -> INR {selected_price:,.2f}")
        else:
            st.caption("Hover for details. Click/tap a point to pin its value below the chart.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Recent Entries</div>', unsafe_allow_html=True)
        table_df = df[["recorded_at", "slot", "rate_22k", "rate_22k_8g", "rate_24k", "rate_24k_8g", "notes"]].copy()
        table_df = table_df.sort_values("recorded_at", ascending=False)
        st.dataframe(table_df.head(20), width="stretch", hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Daily Raise/Decrease (vs Previous Day)</div>', unsafe_allow_html=True)
        daily_change_table = daily_rates.copy()
        daily_change_table["Date"] = pd.to_datetime(daily_change_table["date"]).dt.strftime("%d %b %Y")
        daily_change_table["22K 1g"] = daily_change_table["rate_22k"].map(lambda v: f"{v:,.2f}")
        daily_change_table["22K 1g Change"] = daily_change_table["d_22k_1g"].map(delta_text)
        daily_change_table["22K 8g"] = daily_change_table["rate_22k_8g"].map(lambda v: f"{v:,.2f}")
        daily_change_table["22K 8g Change"] = daily_change_table["d_22k_8g"].map(delta_text)
        daily_change_table["24K 1g"] = daily_change_table["rate_24k"].map(lambda v: f"{v:,.2f}")
        daily_change_table["24K 1g Change"] = daily_change_table["d_24k_1g"].map(delta_text)
        daily_change_table["24K 8g"] = daily_change_table["rate_24k_8g"].map(lambda v: f"{v:,.2f}")
        daily_change_table["24K 8g Change"] = daily_change_table["d_24k_8g"].map(delta_text)
        daily_change_table = daily_change_table.sort_values("date", ascending=False)

        st.dataframe(
            daily_change_table[
                [
                    "Date",
                    "22K 1g",
                    "22K 1g Change",
                    "22K 8g",
                    "22K 8g Change",
                    "24K 1g",
                    "24K 1g Change",
                    "24K 8g",
                    "24K 8g Change",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with main_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Forecast & Decision Support</div>', unsafe_allow_html=True)

        fc1, fc2 = st.columns([1.1, 1.0], gap="small")
        with fc1:
            forecast_scope = st.selectbox(
                "Forecast Range",
                ["Remaining This Month", "Next 30 Days"],
                key="forecast_scope",
            )
        with fc2:
            forecast_unit = st.selectbox(
                "Forecast Unit",
                ["1g", "Sovereign (8g)"],
                key="forecast_unit",
            )

        daily_df = (
            df.groupby("date", as_index=False)[["rate_22k", "rate_24k", "rate_22k_8g", "rate_24k_8g"]]
            .mean()
            .sort_values("date")
        )

        today = pd.Timestamp.now().floor("D")
        if forecast_scope == "Remaining This Month":
            month_end = (today + pd.offsets.MonthEnd(0)).floor("D")
            future_dates = pd.date_range(today + pd.Timedelta(days=1), month_end, freq="D")
        else:
            future_dates = pd.date_range(today + pd.Timedelta(days=1), periods=30, freq="D")

        if forecast_type == "22K" and forecast_unit == "1g":
            value_col = "rate_22k"
            hist_label = "22K 1g"
        elif forecast_type == "24K" and forecast_unit == "1g":
            value_col = "rate_24k"
            hist_label = "24K 1g"
        elif forecast_type == "22K":
            value_col = "rate_22k_8g"
            hist_label = "22K 8g"
        else:
            value_col = "rate_24k_8g"
            hist_label = "24K 8g"

        forecast_df, forecast_model = build_enhanced_forecast(daily_df, future_dates, value_col)

        if forecast_df.empty or len(future_dates) == 0:
            st.info("Not enough data to forecast yet. Keep collecting daily rates and try again.")
        else:
            if forecast_model == "enhanced":
                st.caption("Model: enhanced (lags + weekday seasonality + macro factors + news sentiment)")
            else:
                st.caption("Model: baseline (trend + weekday seasonality)")

            if st.session_state["show_forecast_graph"]:
                history_tail = daily_df[["date", value_col]].rename(columns={value_col: "value"}).tail(45)
                history_tail["series"] = f"Historical {hist_label}"

                forecast_plot = forecast_df[["date", "yhat"]].rename(columns={"yhat": "value"})
                forecast_plot["series"] = f"Forecast {hist_label}"

                combined_forecast = pd.concat([history_tail, forecast_plot], ignore_index=True)
                fig_forecast = px.line(
                    combined_forecast,
                    x="date",
                    y="value",
                    color="series",
                    color_discrete_map={
                        f"Historical {hist_label}": "#7dd3fc",
                        f"Forecast {hist_label}": "#fbbf24",
                    },
                    labels={"date": "Date", "value": "Price (INR)", "series": ""},
                )
                fig_forecast.add_traces(
                    px.line(
                        forecast_df,
                        x="date",
                        y="yhat_lower",
                        color_discrete_sequence=["#64748b"],
                    ).update_traces(showlegend=False, line=dict(width=1, dash="dot")).data
                )
                fig_forecast.add_traces(
                    px.line(
                        forecast_df,
                        x="date",
                        y="yhat_upper",
                        color_discrete_sequence=["#64748b"],
                    ).update_traces(showlegend=False, line=dict(width=1, dash="dot")).data
                )
                fig_forecast.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(6,14,21,0.65)",
                    font=dict(color="#dbeaff"),
                    legend=dict(orientation="h", y=1.08, x=0.01),
                    margin=dict(l=20, r=10, t=10, b=20),
                    xaxis=dict(showgrid=False, linecolor="#334b5d"),
                    yaxis=dict(showgrid=True, gridcolor="#253a4b", linecolor="#334b5d"),
                )
                st.plotly_chart(fig_forecast, width="stretch")
            else:
                st.caption("Click 'Show Forecast Graph' to view predicted price trend and confidence range.")

            f_min = forecast_df.loc[forecast_df["yhat"].idxmin()]
            f_max = forecast_df.loc[forecast_df["yhat"].idxmax()]
            c1, c2 = st.columns(2)
            c1.metric("Forecast Lowest", f"{f_min['yhat']:.2f}", f_min["date"].strftime("%d %b"))
            c2.metric("Forecast Highest", f"{f_max['yhat']:.2f}", f_max["date"].strftime("%d %b"))

            month_start = today.replace(day=1)
            month_hist = daily_df[daily_df["date"] >= month_start].copy()
            if month_hist.empty:
                month_hist = daily_df.copy()

            m_min = month_hist.loc[month_hist[value_col].idxmin()]
            m_max = month_hist.loc[month_hist[value_col].idxmax()]

            buy_date = pd.Timestamp(f_min["date"])
            buy_text = buy_date.strftime("%d %b %Y")
            buy_slot, slot_reason = recommend_buy_time(df, value_col, buy_date)

            detail_left, detail_right = st.columns([1.05, 0.95], gap="medium")

            with detail_left:
                st.markdown("#### Best Time To Purchase")
                st.markdown(
                    f"""
                    <div class="purchase-stack">
                        <div class="purchase-card buy-date">
                            <div class="purchase-head">Best Buy Date</div>
                            <div class="purchase-main">{buy_text}<span class="purchase-badge">Lowest Expected</span></div>
                            <div class="purchase-sub">Projected local minimum for {hist_label}. If flexible, consider buying within +/-1 day.</div>
                        </div>
                        <div class="purchase-card buy-slot">
                            <div class="purchase-head">Best Time On That Date</div>
                            <div class="purchase-main">{buy_slot}</div>
                            <div class="purchase-sub">Around 10 AM for MORNING, 5 PM for EVENING.</div>
                            <div class="purchase-sub">{slot_reason}</div>
                        </div>
                    </div>
                    <div class="purchase-note">Model guidance only. Sudden policy, tax, geopolitical, or market shocks can change prices quickly.</div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("#### Factors Likely To Affect Next Few Days")
                factor_notes = build_factor_outlook(daily_df, value_col, future_dates.max())
                for note in factor_notes:
                    st.markdown(f"- {note}")

            with detail_right:
                st.markdown("#### Forecast Summary Table")
                summary_df = pd.DataFrame(
                    [
                        {
                            "Metric": "Month Lowest",
                            "Value (INR)": float(m_min[value_col]),
                            "Date": pd.Timestamp(m_min["date"]).strftime("%d %b %Y"),
                        },
                        {
                            "Metric": "Month Highest",
                            "Value (INR)": float(m_max[value_col]),
                            "Date": pd.Timestamp(m_max["date"]).strftime("%d %b %Y"),
                        },
                        {
                            "Metric": "Forecast Lowest",
                            "Value (INR)": float(f_min["yhat"]),
                            "Date": pd.Timestamp(f_min["date"]).strftime("%d %b %Y"),
                        },
                        {
                            "Metric": "Forecast Highest",
                            "Value (INR)": float(f_max["yhat"]),
                            "Date": pd.Timestamp(f_max["date"]).strftime("%d %b %Y"),
                        },
                    ]
                )
                summary_df["Value (INR)"] = summary_df["Value (INR)"].map(lambda v: f"{v:,.2f}")
                st.dataframe(summary_df, width="stretch", hide_index=True)

                st.markdown("#### Next Days Forecast Table")
                table_forecast = forecast_df.copy()
                table_forecast["dod_change"] = table_forecast["yhat"].diff()
                table_forecast = table_forecast.rename(
                    columns={
                        "date": "Date",
                        "yhat": "Predicted",
                        "yhat_lower": "Lower",
                        "yhat_upper": "Upper",
                        "dod_change": "Change vs Previous Day",
                    }
                )
                table_forecast["Date"] = pd.to_datetime(table_forecast["Date"]).dt.strftime("%d %b %Y")
                for col in ["Predicted", "Lower", "Upper"]:
                    table_forecast[col] = table_forecast[col].map(lambda v: f"{v:,.2f}")
                table_forecast["Change vs Previous Day"] = table_forecast["Change vs Previous Day"].map(delta_text)
                st.dataframe(table_forecast.head(15), width="stretch", hide_index=True)

        st.markdown('</div>', unsafe_allow_html=True)

        render_manual_entry_launcher(button_key="open_manual_entry_main")
