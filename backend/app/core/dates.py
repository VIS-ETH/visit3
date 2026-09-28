from datetime import date, datetime
from zoneinfo import ZoneInfo

LOCAL_TIMEZONE = ZoneInfo("Europe/Zurich")


def local_today() -> date:
    return datetime.now(LOCAL_TIMEZONE).date()
