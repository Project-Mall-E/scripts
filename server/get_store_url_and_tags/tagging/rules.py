import re
from typing import List, Set, Dict, Optional
from urllib.parse import urlparse, unquote

from ..utils.logger import get_logger

logger = get_logger(__name__)


TAG_RULES: Dict[str, Dict[str, List[str]]] = {
    "gender": {
        "Womens": ["women", "womens", "woman", "womans", "aerie", "aritzia", "ladies", "lady", "female", "her", "w-"],
        "Mens": ["men", "mens", "man", "mans", "guys", "guy", "male", "him", "m-"],
        "Kids": ["kids", "kid", "children", "child", "youth", "junior", "juniors", "boys", "girls", "baby", "babies", "toddler", "toddlers", "infant", "infants"],
        "Unisex": ["unisex", "all-gender", "gender-neutral"],
    },
    "category": {
        "Tops": ["tops", "top", "shirts", "shirt", "blouses", "blouse"],
        "T-Shirts": ["t-shirts", "t-shirt", "tshirts", "tshirt", "tees", "tee"],
        "Bottoms": ["bottoms", "bottom", "pants", "pant", "trousers", "trouser"],
        "Jeans": ["jeans", "jean", "denim"],
        "Shorts": ["shorts", "short"],
        "Skirts": ["skirts", "skirt"],
        "Dresses": ["dresses", "dress", "gowns", "gown", "frocks", "frock", "rompers", "romper", "jumpsuits", "jumpsuit"],
        "Outerwear": ["outerwear", "jackets", "jacket", "coats", "coat", "blazers", "blazer", "parkas", "parka"],
        "Sweaters": ["sweaters", "sweater", "jumpers", "jumper", "pullovers", "pullover", "cardigans", "cardigan", "hoodies", "hoodie", "sweatshirts", "sweatshirt"],
        "Activewear": ["activewear", "athletic", "athletics", "sport", "sports", "workout", "gym", "fitness", "athleisure"],
        "Swimwear": ["swimwear", "swim", "swimsuits", "swimsuit", "bikini", "bikinis", "boardshorts"],
        "Underwear": ["underwear", "intimates", "lingerie", "bras", "bra", "panties", "boxers", "briefs"],
        "Sleepwear": ["sleepwear", "pajamas", "pyjamas", "loungewear", "nightwear", "robes", "robe"],
        "Shoes": ["shoes", "shoe", "footwear", "sneakers", "sneaker", "boots", "boot", "sandals", "sandal", "heels", "flats", "loafers"],
        "Accessories": ["accessories", "accessory", "acc", "accs", "belts", "belt", "hats", "hat", "scarves", "scarf", "gloves", "sunglasses", "watches", "jewelry", "jewellery"],
        "Bags": ["bags", "bag", "purses", "purse", "handbags", "handbag", "totes", "tote", "backpacks", "backpack", "wallets", "wallet", "clutches", "clutch"],
    },
    "occasion": {
        "New Arrivals": ["new-arrivals", "new arrivals", "newarrivals", "new", "just-in", "just in", "whats-new", "what's new", "latest", "fresh-picks"],
        "Sale": ["sale", "sales", "clearance", "discount", "discounts", "outlet", "reduced", "markdown", "markdowns", "promo", "deals"],
        "Trending": ["trending", "trend", "trends", "popular", "best-sellers", "bestsellers", "best sellers", "hot", "top-rated", "favorites", "favourites"],
        "Workwear": ["workwear", "work", "office", "professional", "business", "career"],
        "Casual": ["casual", "everyday", "basics", "essentials"],
        "Formal": ["formal", "dressy", "evening", "occasion", "party", "wedding", "prom"],
        "Vacation": ["vacation", "resort", "travel", "holiday", "beach", "cruise"],
    },
}


class TagExtractor:
    """
    Extracts tags from URLs, page titles, nav text, and breadcrumbs.
    
    Uses rule-based pattern matching against predefined keyword lists.
    """
    
    def __init__(self, rules: Dict[str, Dict[str, List[str]]] = None):
        self.rules = rules or TAG_RULES
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Pre-compile regex patterns for performance."""
        compiled = {}
        
        for dimension, tags in self.rules.items():
            compiled[dimension] = {}
            for tag_name, keywords in tags.items():
                escaped = [re.escape(kw) for kw in keywords]
                pattern = r"(?:^|[-_/\s])(" + "|".join(escaped) + r")(?:[-_/\s]|$)"
                compiled[dimension][tag_name] = re.compile(pattern, re.IGNORECASE)
        
        return compiled
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        text = unquote(text)
        text = text.lower()
        text = re.sub(r"[^\w\s-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def _extract_url_segments(self, url: str) -> str:
        """Extract searchable text from URL path."""
        parsed = urlparse(url)
        path = parsed.path
        path = re.sub(r"/cat\d+", "", path)
        path = re.sub(r"/clr\w+\d+", "", path)
        path = path.replace("/", " ").replace("-", " ").replace("_", " ")
        return self._normalize_text(path)
    
    def extract_from_text(self, text: str) -> Dict[str, Set[str]]:
        """
        Extract tags from arbitrary text.
        
        Args:
            text: Text to search for tag keywords
            
        Returns:
            Dict mapping dimension names to sets of matched tags
        """
        if not text:
            return {}
        
        normalized = self._normalize_text(text)
        results: Dict[str, Set[str]] = {}
        
        for dimension, patterns in self._compiled_patterns.items():
            matched = set()
            for tag_name, pattern in patterns.items():
                if pattern.search(normalized) or pattern.search(text.lower()):
                    matched.add(tag_name)
            if matched:
                results[dimension] = matched
        
        return results
    
    def extract(
        self,
        url: str,
        nav_text: Optional[str] = None,
        page_title: Optional[str] = None,
        breadcrumb_text: Optional[str] = None
    ) -> List[str]:
        """
        Extract tags from all available sources.
        
        Priority: URL path > nav text > page title > breadcrumbs
        
        Args:
            url: The category URL
            nav_text: Text from the navigation link
            page_title: The page's <title> tag content
            breadcrumb_text: Breadcrumb trail text
            
        Returns:
            List of extracted tag names (not yet normalized)
        """
        all_matches: Dict[str, Set[str]] = {
            "gender": set(),
            "category": set(),
            "occasion": set(),
        }
        
        sources = [
            ("url", self._extract_url_segments(url)),
            ("nav_text", nav_text),
            ("page_title", page_title),
            ("breadcrumbs", breadcrumb_text),
        ]
        
        for source_name, text in sources:
            if not text:
                continue
            
            matches = self.extract_from_text(text)
            
            for dimension, tags in matches.items():
                if dimension not in all_matches:
                    all_matches[dimension] = set()
                all_matches[dimension].update(tags)
        
        result = []
        for dimension in ["gender", "category", "occasion"]:
            tags = all_matches.get(dimension, set())
            result.extend(sorted(tags))
        
        logger.debug(f"Extracted tags from {url}: {result}")
        return result
