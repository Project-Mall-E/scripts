import re
from typing import List, Optional, Set
from urllib.parse import urlparse

from ..utils.logger import get_logger

logger = get_logger(__name__)


class URLClassifier:
    """
    Classifies URLs to identify product category pages vs other page types.
    """
    
    CATEGORY_INDICATORS = [
        r"/womens?[-/]",
        r"/mens?[-/]",
        r"/kids?[-/]",
        r"/boys?[-/]",
        r"/girls?[-/]",
        r"/aerie/",
        r"/shop/",
        r"/category/",
        r"/categories/",
        r"/collection/",
        r"/collections/",
        r"/c/",
        r"/cat\d+",
        r"/products?/",
        r"/clothing/",
        r"/apparel/",
        r"[-/](tops?|bottoms?|jeans|dresses?|shoes?|accessories)[-/]?",
        r"[-/](shirts?|pants?|shorts?|skirts?|sweaters?)[-/]?",
        r"[-/](jackets?|coats?|outerwear)[-/]?",
        r"[-/](new-arrivals?|sale|clearance)[-/]?",
    ]
    
    EXCLUDE_PATTERNS = [
        r"/account",
        r"/login",
        r"/signin",
        r"/signup",
        r"/register",
        r"/cart",
        r"/checkout",
        r"/bag",
        r"/wishlist",
        r"/favorites",
        r"/help",
        r"/faq",
        r"/support",
        r"/contact",
        r"/blog",
        r"/article",
        r"/news",
        r"/about",
        r"/careers",
        r"/jobs",
        r"/stores?[-/]?locator",
        r"/find[-/]?store",
        r"/gift[-/]?card",
        r"/giftcard",
        r"/search",
        r"/order",
        r"/returns?",
        r"/shipping",
        r"/privacy",
        r"/terms",
        r"/legal",
        r"/cookie",
        r"/subscription",
        r"/email",
        r"/newsletter",
        r"/loyalty",
        r"/rewards",
        r"[?&]q=",
        r"/pdp/",
        r"/product/[a-z0-9-]+$",
    ]
    
    EXCLUDE_EXTENSIONS = {
        ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".js", ".css", ".json", ".xml", ".ico", ".woff", ".woff2",
        ".ttf", ".eot", ".mp4", ".mp3", ".zip", ".tar", ".gz"
    }
    
    def __init__(
        self,
        extra_category_patterns: List[str] = None,
        extra_exclude_patterns: List[str] = None,
        max_path_depth: Optional[int] = None
    ):
        patterns = self.CATEGORY_INDICATORS + (extra_category_patterns or [])
        self._category_regex = re.compile("|".join(patterns), re.IGNORECASE)
        
        excludes = self.EXCLUDE_PATTERNS + (extra_exclude_patterns or [])
        self._exclude_regex = re.compile("|".join(excludes), re.IGNORECASE)
        
        self._max_path_depth = max_path_depth
    
    def _has_excluded_extension(self, url: str) -> bool:
        """Check if URL ends with an excluded file extension."""
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        return any(path_lower.endswith(ext) for ext in self.EXCLUDE_EXTENSIONS)
    
    def _is_fragment_or_query_only(self, url: str, base_url: str) -> bool:
        """Check if URL differs from base only by fragment or trivial query."""
        parsed = urlparse(url)
        base_parsed = urlparse(base_url)
        
        if parsed.netloc != base_parsed.netloc:
            return False
        
        if parsed.path.rstrip("/") == base_parsed.path.rstrip("/"):
            return True
        
        return False
    
    def is_category_url(self, url: str, base_url: str = None) -> bool:
        """
        Determine if a URL is likely a product category page.
        
        Args:
            url: The URL to classify
            base_url: The store's base URL (to filter out homepage links)
            
        Returns:
            True if the URL appears to be a category page
        """
        if not url or not url.startswith(("http://", "https://")):
            return False
        
        if self._has_excluded_extension(url):
            return False
        
        if "#" in url:
            url = url.split("#")[0]
        
        if base_url and self._is_fragment_or_query_only(url, base_url):
            return False

        if base_url:
            base_parsed = urlparse(base_url)
            url_parsed = urlparse(url)
            base_path_prefix = base_parsed.path.rstrip("/")
            if base_path_prefix and not url_parsed.path.startswith(base_path_prefix):
                logger.debug(f"URL excluded by path prefix mismatch: {url}")
                return False
            if self._max_path_depth is not None:
                url_segments = [s for s in url_parsed.path.strip("/").split("/") if s]
                if len(url_segments) > self._max_path_depth:
                    logger.debug(f"URL excluded by depth ({len(url_segments)} > {self._max_path_depth}): {url}")
                    return False
        
        if self._exclude_regex.search(url):
            logger.debug(f"URL excluded by pattern: {url}")
            return False
        
        if self._category_regex.search(url):
            # #region agent log
            import json as _json, time as _time
            _m = self._category_regex.search(url)
            _log_path = "/home/rob/Coding/all-on/.cursor/debug-4cc033.log"
            try:
                import os as _os
                _os.makedirs(_os.path.dirname(_log_path), exist_ok=True)
                with open(_log_path, "a") as _f:
                    _f.write(_json.dumps({"sessionId": "4cc033", "hypothesisId": "B_C", "location": "url_classifier.py:is_category_url", "message": "URL passed classifier", "data": {"url": url, "matched_pattern": _m.group(0) if _m else None}, "timestamp": int(_time.time() * 1000)}) + "\n")
            except Exception:
                pass
            # #endregion
            return True
        
        return False
    
    def filter_category_urls(
        self,
        urls: List[str],
        base_url: str = None
    ) -> List[str]:
        """
        Filter a list of URLs to only category pages.
        
        Args:
            urls: List of URLs to filter
            base_url: The store's base URL
            
        Returns:
            List of URLs that appear to be category pages
        """
        seen: Set[str] = set()
        result = []
        
        for url in urls:
            normalized = url.rstrip("/").split("#")[0]
            
            if normalized in seen:
                continue
            seen.add(normalized)
            
            if self.is_category_url(url, base_url):
                result.append(url)
        
        logger.info(f"Filtered {len(urls)} URLs to {len(result)} category URLs")
        return result
