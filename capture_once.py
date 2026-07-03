from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from gold_rate_service import GoldRateRecord, fetch_kerala_rates, init_db, upsert_rate

IST = ZoneInfo("Asia/Kolkata")


def resolve_slot(raw_slot: str) -> str:
    slot = (raw_slot or "AUTO").upper().strip()
    if slot in {"MORNING", "EVENING"}:
        return slot

    # AUTO mode: morning before 1 PM IST, evening otherwise.
    current_hour = datetime.now(IST).hour
    return "MORNING" if current_hour < 13 else "EVENING"


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture one Kerala gold-rate snapshot")
    parser.add_argument("--slot", default="AUTO", choices=["AUTO", "MORNING", "EVENING"])
    args = parser.parse_args()

    init_db()
    slot = resolve_slot(args.slot)
    now = datetime.now(IST)

    rate_22k, rate_24k = fetch_kerala_rates()
    upsert_rate(
        GoldRateRecord(
            recorded_at=now,
            slot=slot,
            rate_22k=rate_22k,
            rate_24k=rate_24k,
            notes=f"Scheduled capture via GitHub Actions ({slot})",
        )
    )

    print(f"[{now.isoformat(timespec='seconds')}] Stored {slot}: 22K={rate_22k}, 24K={rate_24k}")


if __name__ == "__main__":
    main()
