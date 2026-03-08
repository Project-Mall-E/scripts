import asyncio
import random
import time
from collections import defaultdict
from typing import Dict

from .logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Per-domain rate limiter to avoid overwhelming servers.
    
    Ensures a minimum delay between requests to the same domain.
    Optional jitter makes wait times less regular (recommended for bot avoidance).
    """
    
    def __init__(self, default_delay: float = 2.0, jitter_seconds: float = 0.0):
        """
        Args:
            default_delay: Minimum seconds between requests to the same domain
            jitter_seconds: Optional ± seconds added to each wait (e.g. 0.2 for ±0.2s)
        """
        self.default_delay = default_delay
        self.jitter_seconds = max(0.0, jitter_seconds)
        self._last_request_time: Dict[str, float] = defaultdict(float)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    async def acquire(self, domain: str) -> None:
        """
        Wait until it's safe to make a request to the given domain.
        
        Args:
            domain: The domain to rate limit (e.g., 'abercrombie.com')
        """
        async with self._locks[domain]:
            now = time.monotonic()
            elapsed = now - self._last_request_time[domain]
            wait_time = self.default_delay - elapsed
            if self.jitter_seconds > 0 and wait_time > 0:
                jitter = random.uniform(-self.jitter_seconds, self.jitter_seconds)
                wait_time = max(0.0, wait_time + jitter)
            
            if wait_time > 0:
                logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            
            self._last_request_time[domain] = time.monotonic()
    
    def reset(self, domain: str = None) -> None:
        """
        Reset rate limit tracking.
        
        Args:
            domain: Specific domain to reset, or None to reset all
        """
        if domain:
            self._last_request_time[domain] = 0
        else:
            self._last_request_time.clear()
