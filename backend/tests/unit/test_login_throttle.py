import pytest

from app.core.exceptions import RateLimited
from app.core.rate_limit import LoginThrottle


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def throttle(clock: Clock) -> LoginThrottle:
    return LoginThrottle(
        failures_before_backoff=3,
        backoff_base_seconds=30,
        backoff_max_seconds=120,
        ip_max_failures=10,
        ip_window_seconds=900,
        clock=clock,
    )


def fail(limiter: LoginThrottle, times: int, ip: str, email: str) -> None:
    for _ in range(times):
        limiter.check(ip, email)
        limiter.record_failure(ip, email)


def test_an_account_backs_off_after_repeated_failures():
    clock = Clock()
    limiter = throttle(clock)
    fail(limiter, 3, "10.0.0.1", "ada@example.com")

    with pytest.raises(RateLimited):
        limiter.check("10.0.0.2", "ada@example.com")
    limiter.check("10.0.0.2", "bob@example.com")


def test_the_backoff_doubles_and_is_capped():
    clock = Clock()
    limiter = throttle(clock)
    fail(limiter, 3, "10.0.0.1", "ada@example.com")
    clock.now += 30
    fail(limiter, 1, "10.0.0.1", "ada@example.com")

    clock.now += 59
    with pytest.raises(RateLimited):
        limiter.check("10.0.0.1", "ada@example.com")
    clock.now += 1
    limiter.check("10.0.0.1", "ada@example.com")
    for _ in range(5):
        limiter.record_failure("10.0.0.1", "ada@example.com")
    clock.now += 120
    limiter.check("10.0.0.1", "ada@example.com")


def test_a_successful_login_clears_the_account_failures():
    clock = Clock()
    limiter = throttle(clock)
    fail(limiter, 2, "10.0.0.1", "ada@example.com")
    limiter.record_success("ada@example.com")
    fail(limiter, 2, "10.0.0.1", "ada@example.com")

    limiter.check("10.0.0.1", "ada@example.com")


def test_one_address_cannot_spray_many_accounts():
    clock = Clock()
    limiter = throttle(clock)
    for index in range(10):
        fail(limiter, 1, "10.0.0.1", f"user{index}@example.com")

    with pytest.raises(RateLimited):
        limiter.check("10.0.0.1", "fresh@example.com")
    limiter.check("10.0.0.2", "fresh@example.com")
    clock.now += 900
    limiter.check("10.0.0.1", "fresh@example.com")


def test_account_keys_ignore_case():
    clock = Clock()
    limiter = throttle(clock)
    fail(limiter, 3, "10.0.0.1", "Ada@Example.com")

    with pytest.raises(RateLimited):
        limiter.check("10.0.0.1", "ada@example.com")
