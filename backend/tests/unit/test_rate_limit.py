from starlette.requests import Request

from app.core.rate_limit import SlidingWindowRateLimiter, client_host


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _limiter(clock: FakeClock, limit: int = 3, window: float = 60.0):
    return SlidingWindowRateLimiter(limit, window, clock)


def test_allows_up_to_the_limit_inside_the_window():
    clock = FakeClock()
    limiter = _limiter(clock)

    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]


def test_window_slides_instead_of_resetting_in_blocks():
    clock = FakeClock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.allow("a")
        clock.advance(10)

    clock.advance(29)

    assert limiter.allow("a") is False
    clock.advance(1)
    assert limiter.allow("a") is True


def test_allows_again_once_the_window_has_passed():
    clock = FakeClock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.allow("a")

    clock.advance(60)

    assert limiter.allow("a") is True


def test_keys_are_counted_independently():
    clock = FakeClock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.allow("a")

    assert limiter.allow("a") is False
    assert limiter.allow("b") is True


def test_reset_clears_all_keys():
    clock = FakeClock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.allow("a")

    limiter.reset()

    assert limiter.allow("a") is True


def test_idle_keys_are_dropped_once_their_window_empties():
    clock = FakeClock()
    limiter = _limiter(clock)
    limiter.allow("a")
    limiter.allow("b")

    clock.advance(60)
    limiter.allow("c")

    assert limiter.tracked_keys == 1


def test_a_key_survives_while_its_window_still_holds_hits():
    clock = FakeClock()
    limiter = _limiter(clock)
    limiter.allow("a")

    clock.advance(59)
    limiter.allow("b")

    assert limiter.tracked_keys == 2


def test_the_number_of_tracked_keys_is_capped():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 60.0, clock, max_keys=2)
    for key in ("a", "b", "c"):
        limiter.allow(key)
        clock.advance(1)

    assert limiter.tracked_keys == 2


def test_the_oldest_key_is_evicted_first():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(1, 60.0, clock, max_keys=2)
    for key in ("a", "b", "c"):
        limiter.allow(key)
        clock.advance(1)

    assert limiter.allow("a") is True
    assert limiter.allow("c") is False


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": (peer, 40000),
        }
    )


def test_a_direct_peer_cannot_spoof_its_key_with_forwarded_for():
    request = _request("203.0.113.9", "198.51.100.7")

    assert client_host(request, []) == "203.0.113.9"


def test_a_trusted_proxy_is_keyed_by_the_forwarded_client():
    request = _request("10.0.0.1", "198.51.100.7")

    assert client_host(request, ["10.0.0.1"]) == "198.51.100.7"


def test_trailing_trusted_hops_are_skipped():
    request = _request("10.0.0.1", "198.51.100.7, 10.0.0.2, 10.0.0.3")

    assert client_host(request, ["10.0.0.1", "10.0.0.2", "10.0.0.3"]) == "198.51.100.7"


def test_only_the_last_untrusted_hop_counts():
    request = _request("10.0.0.1", "198.51.100.7, 203.0.113.9")

    assert client_host(request, ["10.0.0.1"]) == "203.0.113.9"


def test_a_trusted_proxy_without_the_header_keeps_its_own_address():
    request = _request("10.0.0.1")

    assert client_host(request, ["10.0.0.1"]) == "10.0.0.1"
