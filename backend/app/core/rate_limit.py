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


def reset_rate_limiters() -> None:
    for limiter in _limiters:
        limiter.reset()


def _new_limiter() -> SlidingWindowRateLimiter:
    settings = get_settings()
    limiter = SlidingWindowRateLimiter(
        settings.RATE_LIMIT_MAX_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS
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


def client_rate_limit(scope: str):
    limiter = _new_limiter()

    async def dependency(request: Request) -> None:
        proxies = get_settings().RATE_LIMIT_TRUSTED_PROXIES
        _enforce(limiter, scope, client_host(request, proxies))

    return Depends(dependency)


def user_rate_limit(scope: str):
    limiter = _new_limiter()

    async def dependency(current_user: CurrentUserDep) -> None:
        _enforce(limiter, scope, str(current_user.id))

    return Depends(dependency)
