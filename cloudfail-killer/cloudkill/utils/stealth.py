"""
CloudFail-Killer - Stealth Module

Provides anti-detection capabilities:
- Random delays between requests
- User-Agent rotation
- Tor proxy support
"""

from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger(__name__)

# Curated User-Agent strings (same list as engine.py for consistency)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0",
]


class StealthManager:
    """
    Manages stealth-related behavior.

    Usage:
        stealth = StealthManager(min_delay=0.5, max_delay=2.0, enabled=True)
        await stealth.delay()  # Random sleep
        ua = stealth.random_ua()  # Random User-Agent
    """

    def __init__(
        self,
        enabled: bool = False,
        min_delay: float = 0.5,
        max_delay: float = 2.0,
    ) -> None:
        self.enabled = enabled
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._ua_index = random.randint(0, len(USER_AGENTS) - 1)

    async def delay(self) -> None:
        """Apply a random delay if stealth is enabled."""
        if not self.enabled:
            return

        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
        logger.debug("Stealth delay: %.2fs", delay)

    def random_ua(self) -> str:
        """Get a random User-Agent string (rotates through list)."""
        self._ua_index = (self._ua_index + 1) % len(USER_AGENTS)
        return USER_AGENTS[self._ua_index]

    @staticmethod
    def get_tor_proxy(port: int = 9050) -> str:
        """Get SOCKS5 proxy URL for Tor."""
        return f"socks5://127.0.0.1:{port}"

    def get_proxy(self) -> str | None:
        """Get proxy URL if stealth is enabled."""
        return self.get_tor_proxy() if self.enabled else None
