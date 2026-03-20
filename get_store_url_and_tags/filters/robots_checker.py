import asyncio
from typing import Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import aiohttp

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RobotsChecker:
    """
    Checks URLs against robots.txt rules.
    
    Caches robots.txt content per domain to avoid repeated fetches.
    """
    
    USER_AGENT = "ClothingAggregatorBot/1.0"
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._parsers: Dict[str, Optional[RobotFileParser]] = {}
        self._fetch_locks: Dict[str, asyncio.Lock] = {}
    
    def _get_robots_url(self, url: str) -> str:
        """Get the robots.txt URL for a given URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc
    
    async def _fetch_robots(self, domain: str, robots_url: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt for a domain."""
        if domain not in self._fetch_locks:
            self._fetch_locks[domain] = asyncio.Lock()
        
        async with self._fetch_locks[domain]:
            if domain in self._parsers:
                return self._parsers[domain]
            
            parser = RobotFileParser()
            parser.set_url(robots_url)
            
            try:
                async with aiohttp.ClientSession() as session:
                    request = session.get(
                        robots_url,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        headers={"User-Agent": self.USER_AGENT}
                    )
                    if hasattr(request, "__aenter__"):
                        async with request as response:
                            if response.status == 200:
                                content = await response.text()
                                parser.parse(content.splitlines())
                                logger.debug(f"Loaded robots.txt for {domain}")
                            else:
                                logger.debug(
                                    f"No robots.txt for {domain} (status {response.status}), "
                                    "allowing all URLs"
                                )
                                parser = None
                    else:
                        response = await request
                        if response.status == 200:
                            content = await response.text()
                            parser.parse(content.splitlines())
                            logger.debug(f"Loaded robots.txt for {domain}")
                        else:
                            logger.debug(
                                f"No robots.txt for {domain} (status {response.status}), "
                                "allowing all URLs"
                            )
                            parser = None
            except Exception as e:
                logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
                parser = None
            
            self._parsers[domain] = parser
            return parser
    
    async def is_allowed(self, url: str) -> bool:
        """
        Check if a URL is allowed by robots.txt.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL is allowed (or robots.txt doesn't exist/couldn't be fetched)
        """
        domain = self._get_domain(url)
        robots_url = self._get_robots_url(url)
        
        parser = await self._fetch_robots(domain, robots_url)
        
        if parser is None:
            return True
        
        allowed = parser.can_fetch(self.USER_AGENT, url)
        if not allowed:
            logger.info(f"URL blocked by robots.txt: {url}")
        
        return allowed
    
    async def filter_allowed(self, urls: list[str]) -> list[str]:
        """
        Filter a list of URLs to only those allowed by robots.txt.
        
        Args:
            urls: List of URLs to filter
            
        Returns:
            List of allowed URLs
        """
        results = await asyncio.gather(*[self.is_allowed(url) for url in urls])
        return [url for url, allowed in zip(urls, results) if allowed]
    
    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._parsers.clear()
