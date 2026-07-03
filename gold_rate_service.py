from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional
import tomllib

import requests
from bs4 import BeautifulSoup

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional dependency in local setups
    psycopg = None
    dict_row = None

DB_PATH = Path(__file__).parent / "gold_rates.db"
SOURCE_URL = "https://www.goodreturns.in/gold-rates/kerala.html"
TIMEOUT_SECONDS = 20
AJAX_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "X-OIGT-Header": "GITPL",
    "User-Agent": "Mozilla/5.0",
    "Referer": SOURCE_URL,
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def _load_database_url() -> Optional[str]:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        db_url = os.getenv("SUPABASE_DB_URL", "").strip()

    if not db_url:
        candidates = [
            Path.cwd() / ".streamlit" / "secrets.toml",
            Path.home() / ".streamlit" / "secrets.toml",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                db_url = str(data.get("DATABASE_URL", "")).strip()
                if db_url:
                    break
            except Exception:
                continue

    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]

    return db_url or None


def _use_postgres() -> bool:
    return _load_database_url() is not None


def _pg_connect():
    db_url = _load_database_url()
    if not db_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Add psycopg[binary] to requirements.")
    return psycopg.connect(db_url)


@dataclass
class GoldRateRecord:
    recorded_at: datetime
    slot: str
    rate_22k: float
    rate_24k: float
    source_url: str = SOURCE_URL
    notes: str = ""


def init_db() -> None:
    if _use_postgres():
        conn = _pg_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rates (
                        id BIGSERIAL PRIMARY KEY,
                        recorded_at TEXT NOT NULL,
                        date_key TEXT NOT NULL,
                        slot TEXT NOT NULL,
                        rate_22k DOUBLE PRECISION NOT NULL,
                        rate_24k DOUBLE PRECISION NOT NULL,
                        source_url TEXT NOT NULL,
                        notes TEXT,
                        UNIQUE(date_key, slot)
                    )
                    """
                )
            conn.commit()
        finally:
            conn.close()
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                date_key TEXT NOT NULL,
                slot TEXT NOT NULL,
                rate_22k REAL NOT NULL,
                rate_24k REAL NOT NULL,
                source_url TEXT NOT NULL,
                notes TEXT,
                UNIQUE(date_key, slot)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _extract_numeric_values(text: str) -> list[float]:
    values = []
    for match in re.findall(r"(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.\d+)?)", text, re.IGNORECASE):
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    return values


def _normalize_price(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"([0-9,]+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def fetch_kerala_rates() -> tuple[float, float]:
    """
    Fetches Kerala 22K and 24K gold rates.

    The parser is intentionally defensive because the source page structure can change.
    If parsing fails, it raises ValueError.
    """
    session = requests.Session()

    # Warm up cookies/session to reduce 403 responses from bot protection.
    session.get(SOURCE_URL, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "Mozilla/5.0"})

    response = session.get(
        SOURCE_URL,
        timeout=TIMEOUT_SECONDS,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": SOURCE_URL,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # Strategy 1: parse around 22K/24K sections if present.
    compact = re.sub(r"\s+", " ", page_text)

    candidate_22k = re.findall(
        r"22\s*K[^₹RsINR]*?(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.\d+)?)",
        compact,
        flags=re.IGNORECASE,
    )
    candidate_24k = re.findall(
        r"24\s*K[^₹RsINR]*?(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.\d+)?)",
        compact,
        flags=re.IGNORECASE,
    )

    if candidate_22k and candidate_24k:
        rate_22k = float(candidate_22k[0].replace(",", ""))
        rate_24k = float(candidate_24k[0].replace(",", ""))
        return rate_22k, rate_24k

    # Strategy 2: fallback to all currency values and infer ordering.
    values = _extract_numeric_values(compact)
    values = [v for v in values if 1000 <= v <= 20000]
    unique_values = list(dict.fromkeys(values))

    if len(unique_values) >= 2:
        # Most pages list 22K first and 24K next; if uncertain, sort ascending.
        v1, v2 = unique_values[0], unique_values[1]
        low, high = sorted([v1, v2])
        return low, high

    # Final fallback: use the date-wise JSON endpoint for today.
    try:
        return fetch_kerala_rates_for_date(datetime.now().date(), session=session)
    except Exception as exc:
        raise ValueError("Could not parse Kerala gold rates from source page.") from exc


def fetch_kerala_rates_for_date(
    target_date: date,
    session: Optional[requests.Session] = None,
) -> tuple[float, float]:
    local_session = session or requests.Session()

    # Source requires session cookies from base page for date-wise AJAX calls.
    if session is None:
        local_session.get(SOURCE_URL, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "Mozilla/5.0"})

    params = {
        "gr_db_dynamic_content": "metal_past_price",
        "date": target_date.strftime("%Y-%m-%d"),
    }
    response = local_session.get(
        SOURCE_URL,
        params=params,
        headers=AJAX_HEADERS,
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    # Preferred path: endpoint returns JSON for selected date.
    try:
        payload = response.json()
        r22 = _normalize_price(payload.get("gold_price_22K") or payload.get("current_price_22K"))
        r24 = _normalize_price(payload.get("gold_price_24K") or payload.get("current_price_24K"))
        if r22 is not None and r24 is not None:
            return r22, r24
    except ValueError:
        pass

    # Fallback path: HTML fragment response.
    text = response.text
    values = _extract_numeric_values(text)
    values = [v for v in values if 1000 <= v <= 20000]
    unique_values = list(dict.fromkeys(values))
    if len(unique_values) >= 2:
        low, high = sorted(unique_values[:2])
        return low, high

    raise ValueError(f"Could not parse historical Kerala rates for {target_date.isoformat()}.")


def backfill_recent_days(days: int = 30, include_today: bool = True) -> dict:
    init_db()
    inserted = 0
    failed = 0
    end_offset = 0 if include_today else 1
    session = requests.Session()
    session.get(SOURCE_URL, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "Mozilla/5.0"})

    for offset in range(end_offset, days + end_offset):
        target_date = (datetime.now() - timedelta(days=offset)).date()
        try:
            rate_22k, rate_24k = fetch_kerala_rates_for_date(target_date, session=session)
            timestamp = datetime.combine(target_date, time(hour=12, minute=0, second=0))
            slot = f"HISTORY_{target_date.strftime('%Y%m%d')}"
            upsert_rate(
                GoldRateRecord(
                    recorded_at=timestamp,
                    slot=slot,
                    rate_22k=rate_22k,
                    rate_24k=rate_24k,
                    notes="Historical backfill from source",
                )
            )
            inserted += 1
        except Exception:
            failed += 1

    return {"inserted": inserted, "failed": failed, "days": days}


def ensure_recent_history(days: int = 30, include_today: bool = False) -> dict:
    """
    Ensures recent day-wise history exists in DB by fetching only missing dates.
    This keeps the app history available without re-fetching already stored days.
    """
    init_db()
    if _use_postgres():
        conn = _pg_connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT date_key FROM rates")
                existing_dates = {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        try:
            existing_dates = {
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT date_key FROM rates"
                ).fetchall()
            }
        finally:
            conn.close()

    inserted = 0
    failed = 0
    skipped = 0

    end_offset = 0 if include_today else 1
    session = requests.Session()
    session.get(SOURCE_URL, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "Mozilla/5.0"})

    for offset in range(end_offset, days + end_offset):
        target_date = (datetime.now() - timedelta(days=offset)).date()
        date_key = target_date.strftime("%Y-%m-%d")

        if date_key in existing_dates:
            skipped += 1
            continue

        try:
            rate_22k, rate_24k = fetch_kerala_rates_for_date(target_date, session=session)
            timestamp = datetime.combine(target_date, time(hour=12, minute=0, second=0))
            slot = f"HISTORY_{target_date.strftime('%Y%m%d')}"
            upsert_rate(
                GoldRateRecord(
                    recorded_at=timestamp,
                    slot=slot,
                    rate_22k=rate_22k,
                    rate_24k=rate_24k,
                    notes="Auto ensure recent history",
                )
            )
            inserted += 1
        except Exception:
            failed += 1

    return {
        "inserted": inserted,
        "failed": failed,
        "skipped": skipped,
        "days": days,
    }


def upsert_rate(record: GoldRateRecord) -> None:
    date_key = record.recorded_at.strftime("%Y-%m-%d")

    if _use_postgres():
        conn = _pg_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rates (recorded_at, date_key, slot, rate_22k, rate_24k, source_url, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(date_key, slot) DO UPDATE SET
                        recorded_at=excluded.recorded_at,
                        rate_22k=excluded.rate_22k,
                        rate_24k=excluded.rate_24k,
                        source_url=excluded.source_url,
                        notes=excluded.notes
                    """,
                    (
                        record.recorded_at.isoformat(timespec="seconds"),
                        date_key,
                        record.slot,
                        record.rate_22k,
                        record.rate_24k,
                        record.source_url,
                        record.notes,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO rates (recorded_at, date_key, slot, rate_22k, rate_24k, source_url, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date_key, slot) DO UPDATE SET
                recorded_at=excluded.recorded_at,
                rate_22k=excluded.rate_22k,
                rate_24k=excluded.rate_24k,
                source_url=excluded.source_url,
                notes=excluded.notes
            """,
            (
                record.recorded_at.isoformat(timespec="seconds"),
                date_key,
                record.slot,
                record.rate_22k,
                record.rate_24k,
                record.source_url,
                record.notes,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def read_rates(month: Optional[str] = None) -> list[dict]:
    if _use_postgres():
        conn = _pg_connect()
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                if month:
                    cur.execute(
                        """
                        SELECT * FROM rates
                        WHERE substring(recorded_at from 1 for 7) = %s
                        ORDER BY recorded_at ASC
                        """,
                        (month,),
                    )
                else:
                    cur.execute("SELECT * FROM rates ORDER BY recorded_at ASC")
                return list(cur.fetchall())
        finally:
            conn.close()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if month:
            rows = conn.execute(
                """
                SELECT * FROM rates
                WHERE strftime('%Y-%m', recorded_at) = ?
                ORDER BY recorded_at ASC
                """,
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM rates ORDER BY recorded_at ASC"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def latest_rate() -> Optional[dict]:
    if _use_postgres():
        conn = _pg_connect()
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM rates ORDER BY recorded_at DESC LIMIT 1")
                row = cur.fetchone()
                return row if row else None
        finally:
            conn.close()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM rates ORDER BY recorded_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_manual_rate(
    rate_22k: float,
    rate_24k: float,
    recorded_at: Optional[datetime] = None,
    slot: Optional[str] = None,
    notes: str = "Manual entry from dashboard",
) -> None:
    timestamp = recorded_at or datetime.now()
    normalized_slot = (slot or f"MANUAL_{timestamp.strftime('%H%M%S')}").strip().upper().replace(" ", "_")
    record = GoldRateRecord(
        recorded_at=timestamp,
        slot=normalized_slot,
        rate_22k=rate_22k,
        rate_24k=rate_24k,
        notes=notes,
    )
    upsert_rate(record)
