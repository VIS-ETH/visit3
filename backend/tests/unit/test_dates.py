from datetime import date, datetime, timezone

import pytest

from app.core.dates import local_today


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        (datetime(2026, 9, 27, 21, 59, tzinfo=timezone.utc), date(2026, 9, 27)),
        (datetime(2026, 9, 27, 22, 37, tzinfo=timezone.utc), date(2026, 9, 28)),
        (datetime(2026, 12, 31, 23, 0, tzinfo=timezone.utc), date(2027, 1, 1)),
    ],
)
def test_local_today_follows_the_zurich_calendar(freeze_now, instant, expected):
    freeze_now(instant)

    assert local_today() == expected
