import time
from collections import OrderedDict, deque
from collections.abc import Callable, Sequence

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.deps import CurrentUserDep
from app.core.exceptions import RateLimited

MAX_TRACKED_KEYS = 10_000

_limiters: list["SlidingWindowRateLimiter"] = []


class SlidingWindowRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = MAX_TRACKED_KEYS,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.max_keys = max_keys
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    @property
    def tracked_keys(self) -> int:
        return len(self._hits)

    def allow(self, key: str) -> bool:
        now = self.clock()
        self._drop_emptied_windows(now)
        hits = self._hits.get(key, deque())
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        self._hits[key] = hits
        self._hits.move_to_end(key)
        self._drop_overflow()
        return True

    def exhausted(self, key: str) -> bool:
        now = self.clock()
        hits = self._hits.get(key)
        if hits is None:
            return False
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()
        return len(hits) >= self.limit

    def reset(self) -> None:
        self._hits.clear()

    def _drop_emptied_windows(self, now: float) -> None:
        while self._hits:
            key, hits = next(iter(self._hits.items()))
            if now - hits[-1] < self.window_seconds:
                return
            del self._hits[key]

    def _drop_overflow(self) -> None:
        while len(self._hits) > self.max_keys:
            self._hits.popitem(last=False)


class LoginThrottle:
    def __init__(
        self,
        failures_before_backoff: int,
        backoff_base_seconds: float,
        backoff_max_seconds: float,
        ip_max_failures: int,
        ip_window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = MAX_TRACKED_KEYS,
    ) -> None:
        self.failures_before_backoff = failures_before_backoff
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_max_seconds = backoff_max_seconds
        self.clock = clock
        self.max_keys = max_keys
        self._accounts: OrderedDict[str, tuple[int, float]] = OrderedDict()
        self._addresses = SlidingWindowRateLimiter(
            ip_max_failures, ip_window_seconds, clock, max_keys
        )

    def check(self, ip: str, email: str) -> None:
        if self._addresses.exhausted(ip):
            raise RateLimited(f"login:address:{ip}")
        _, blocked_until = self._accounts.get(self._account(email), (0, 0.0))
        if self.clock() < blocked_until:
            raise RateLimited(f"login:account:{self._account(email)}")

    def record_failure(self, ip: str, email: str) -> None:
        self._addresses.allow(ip)
        key = self._account(email)
        failures = self._accounts.get(key, (0, 0.0))[0] + 1
        blocked_until = 0.0
        if failures >= self.failures_before_backoff:
            exponent = failures - self.failures_before_backoff
            delay = min(
                self.backoff_base_seconds * 2 ** min(exponent, 32),
                self.backoff_max_seconds,
            )
            blocked_until = self.clock() + delay
        self._accounts[key] = (failures, blocked_until)
        self._accounts.move_to_end(key)
        while len(self._accounts) > self.max_keys:
            self._accounts.popitem(last=False)

    def record_success(self, email: str) -> None:
        self._accounts.pop(self._account(email), None)

    def reset(self) -> None:
        self._accounts.clear()
        self._addresses.reset()

    def _account(self, email: str) -> str:
        return email.strip().lower()


def reset_rate_limiters() -> None:
    for limiter in _limiters:
        limiter.reset()
    login_throttle.reset()


def _new_limiter(
    limit: int | None = None, window_seconds: float | None = None
) -> SlidingWindowRateLimiter:
    settings = get_settings()
    limiter = SlidingWindowRateLimiter(
        limit if limit is not None else settings.RATE_LIMIT_MAX_REQUESTS,
        window_seconds
        if window_seconds is not None
        else settings.RATE_LIMIT_WINDOW_SECONDS,
    )
    _limiters.append(limiter)
    return limiter


def _enforce(limiter: SlidingWindowRateLimiter, scope: str, key: str) -> None:
    if not limiter.allow(f"{scope}:{key}"):
        raise RateLimited(f"{scope}:{key}")


def client_host(request: Request, trusted_proxies: Sequence[str]) -> str:
    peer = request.client.host if request.client else "unknown"
    if peer not in trusted_proxies:
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    for hop in reversed(forwarded.split(",")):
        candidate = hop.strip()
        if candidate and candidate not in trusted_proxies:
            return candidate
    return peer


def new_login_throttle() -> LoginThrottle:
    settings = get_settings()
    return LoginThrottle(
        failures_before_backoff=settings.LOGIN_FAILURES_BEFORE_BACKOFF,
        backoff_base_seconds=settings.LOGIN_BACKOFF_BASE_SECONDS,
        backoff_max_seconds=settings.LOGIN_BACKOFF_MAX_SECONDS,
        ip_max_failures=settings.LOGIN_IP_MAX_FAILURES,
        ip_window_seconds=settings.LOGIN_IP_WINDOW_SECONDS,
    )


login_throttle = new_login_throttle()


def request_client(request: Request) -> str:
    return client_host(request, get_settings().RATE_LIMIT_TRUSTED_PROXIES)


def client_rate_limit(scope: str):
    limiter = _new_limiter()

    async def dependency(request: Request) -> None:
        proxies = get_settings().RATE_LIMIT_TRUSTED_PROXIES
        _enforce(limiter, scope, client_host(request, proxies))

    return Depends(dependency)


def user_rate_limit(
    scope: str, limit: int | None = None, window_seconds: float | None = None
):
    limiter = _new_limiter(limit, window_seconds)

    async def dependency(current_user: CurrentUserDep) -> None:
        _enforce(limiter, scope, str(current_user.id))

    return Depends(dependency)
