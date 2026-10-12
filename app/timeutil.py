"""
One place that decides "what is today?" for the whole app.

Before: unlock dates were compared with the UTC date, so in India (UTC+05:30) a letter set for
10 Oct opened at 05:30 AM IST on 10 Oct. Daily question / special dates used the SERVER's local date,
which is UTC on most hosting (Render) -> wrong day between 00:00 and 05:30 IST.

Now: everything uses the app time zone (default Asia/Kolkata = IST). Change with  APP_TIMEZONE=<name>  in .env.
A letter dated 10 Oct unlocks at 00:00 IST on 10 Oct. (We store only a DATE, not a time of day.)
"""
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()
_NAME = os.environ.get('APP_TIMEZONE', 'Asia/Kolkata').strip() or 'Asia/Kolkata'


def _load_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(_NAME)
    except Exception:
        # Windows without the "tzdata" package has no zone database.
        # India has no daylight saving, so a fixed +05:30 offset is exactly right.
        if _NAME == 'Asia/Kolkata':
            return timezone(timedelta(hours=5, minutes=30), 'IST')
        return timezone.utc


APP_TZ = _load_tz()


def app_now(now_utc=None):
    """Current time in the app time zone. (now_utc is only for tests.)"""
    now_utc = now_utc or datetime.now(timezone.utc)
    return now_utc.astimezone(APP_TZ)


def app_today(now_utc=None):
    return app_now(now_utc).date()


def to_app_date(naive_utc_datetime):
    """A database datetime (naive, stored as UTC) -> the calendar date in the app time zone."""
    return naive_utc_datetime.replace(tzinfo=timezone.utc).astimezone(APP_TZ).date()
