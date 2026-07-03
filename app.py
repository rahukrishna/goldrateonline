from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

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


def render_manual_form() -> None:
    with st.form("manual_rate_form"):
        top1, top2, top3 = st.columns([1.05, 0.95, 0.9])
        now_local = datetime.now()
        with top1:
            entry_date = st.date_input("Date", value=now_local.date())
        with top2:
            entry_time = st.time_input("Time", value=now_local.replace(second=0, microsecond=0).time())
        with top3:
            slot_choice = st.selectbox("Slot", ["AUTO", "MORNING", "EVENING", "CUSTOM"])

        custom_slot = ""
        if slot_choice == "CUSTOM":
            custom_slot = st.text_input("Custom Slot Name", placeholder="NOON_CHECK")

        p1, p2 = st.columns(2)
        with p1:
            rate_22k = st.number_input("22K Rate (INR)", min_value=0.0, step=1.0)
        with p2:
            rate_24k = st.number_input("24K Rate (INR)", min_value=0.0, step=1.0)

        manual_notes = st.text_input("Notes", value="Manual entry from dashboard")
        submitted = st.form_submit_button("Save Manual Rate", use_container_width=True)

        if submitted:
            entry_datetime = datetime.combine(entry_date, entry_time)

            if slot_choice == "AUTO":
                slot_value = f"MANUAL_{entry_datetime.strftime('%H%M%S')}"
            elif slot_choice == "CUSTOM":
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
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Manual Entry</div>', unsafe_allow_html=True)
    render_manual_form()
    st.markdown('</div>', unsafe_allow_html=True)
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

    left_col, right_col = st.columns([1.05, 1.0], gap="medium")

    with left_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Current Price</div>', unsafe_allow_html=True)

        cp1, cp2 = st.columns(2)
        render_price_card(cp1, "22K Pure Gold (916 Hallmarked)", latest["rate_22k"], latest["rate_22k"] * 8, delta_22)
        render_price_card(cp2, "24K Fine Gold (99.9% Purity)", latest["rate_24k"], latest["rate_24k"] * 8, delta_24)

        st.markdown(f'<div class="status-ok">{live_status}</div>', unsafe_allow_html=True)
        st.metric("Last Updated", latest["recorded_at"])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Monthly Stats</div>', unsafe_allow_html=True)

        stats_html = (
            '<div class="stats-grid">'
            + stat_card("Lowest 22K", low_22_value, low_22_date)
            + stat_card("Highest 22K", high_22_value, high_22_date)
            + stat_card("Lowest 24K", low_24_value, low_24_date)
            + stat_card("Highest 24K", high_24_value, high_24_date)
            + "</div>"
        )
        st.markdown(stats_html, unsafe_allow_html=True)
        st.markdown('<div class="helper">Trend badges: green for raise, red for fall, blue for no change.</div>', unsafe_allow_html=True)

        table_df = df[["recorded_at", "slot", "rate_22k", "rate_22k_8g", "rate_24k", "rate_24k_8g", "notes"]].copy()
        table_df = table_df.sort_values("recorded_at", ascending=False)
        st.dataframe(table_df, width="stretch", hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        ctrl1, ctrl2 = st.columns([1, 1])
        with ctrl1:
            unit_choice = st.radio("Unit", ["1g", "Sovereign"], horizontal=True)
        with ctrl2:
            period_choice = st.radio(
                "Range",
                ["1 Week", "1 Month", "This Month", "6 Months", "1 Year", "All"],
                horizontal=True,
            )

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
        render_manual_form()
        st.markdown('</div>', unsafe_allow_html=True)
