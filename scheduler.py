from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from gold_rate_service import GoldRateRecord, fetch_kerala_rates, init_db, upsert_rate

IST = ZoneInfo("Asia/Kolkata")


def _run_for_slot(slot: str) -> None:
    now = datetime.now(IST)
    try:
        rate_22k, rate_24k = fetch_kerala_rates()
        record = GoldRateRecord(
            recorded_at=now,
            slot=slot,
            rate_22k=rate_22k,
            rate_24k=rate_24k,
            notes=f"Auto captured at {slot}",
        )
        upsert_rate(record)
        print(f"[{now}] Stored {slot}: 22K={rate_22k}, 24K={rate_24k}")
    except Exception as exc:
        print(f"[{now}] Failed {slot} update: {exc}")


def morning_job() -> None:
    _run_for_slot("MORNING")


def evening_job() -> None:
    _run_for_slot("EVENING")


def main() -> None:
    init_db()

    scheduler = BlockingScheduler(timezone=IST)
    scheduler.add_job(morning_job, CronTrigger(hour=10, minute=0))
    scheduler.add_job(evening_job, CronTrigger(hour=17, minute=0))

    print("Gold rate scheduler started. Jobs: 10:00 and 17:00 IST daily.")
    print("Press Ctrl+C to stop.")
    scheduler.start()


if __name__ == "__main__":
    main()
