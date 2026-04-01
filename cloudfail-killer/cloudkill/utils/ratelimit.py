"""
CloudFail-Killer - Rate Limiter

Token bucket rate limiter for controlling request rates per source.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket rate limiter."""

    rate: float = 1.0  # requests per second
    burst: int = 3  # max burst size
    _tokens: float = 0.0
    _last_refill: float = 0.0
    _lock: asyncio.Lock | None = None

    def __post_init__(self) -> None:
        self._tokens = float(self.burst)
        self._last_refill = time.monotonic()
        self._lock = None

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self.lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            # Calculate wait time
            deficit = 1.0 - self._tokens
            wait_time = deficit / self.rate
            await asyncio.sleep(wait_time)
            self._tokens = 0.0


class RateLimiter:
    """
    Multi-source rate limiter.

    Usage:
        limiter = RateLimiter(default_rate=1.0)
        limiter.register("crtsh", rate=0.5)  # 0.5 req/s for crt.sh
        await limiter.wait("crtsh")  # Wait before request
    """

    def __init__(self, default_rate: float = 1.0, default_burst: int = 3) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._default_rate = default_rate
        self._default_burst = default_burst

    def register(self, source: str, rate: float | None = None, burst: int | None = None) -> None:
        """Register a rate limiter for a source."""
        self._buckets[source] = TokenBucket(
            rate=rate if rate is not None else self._default_rate,
            burst=burst if burst is not None else self._default_burst,
        )

    async def wait(self, source: str) -> None:
        """Wait for rate limit on a source. Auto-registers if needed."""
        if source not in self._buckets:
            self.register(source)
        await self._buckets[source].acquire()

    def get_stats(self) -> dict[str, dict]:
        """Get stats for all registered sources."""
        return {
            name: {"rate": b.rate, "burst": b.burst, "tokens": round(b._tokens, 2)}
            for name, b in self._buckets.items()
        }
