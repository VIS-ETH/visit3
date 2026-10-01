from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_TIMEZONE = ZoneInfo("Europe/Zurich")


def local_today() -> date:
    return datetime.now(LOCAL_TIMEZONE).date()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TIMEZONE)
    return value.astimezone(timezone.utc)
