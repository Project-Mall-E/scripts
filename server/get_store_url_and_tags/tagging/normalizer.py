from typing import List, Dict, Set, Optional
from difflib import SequenceMatcher

from ..utils.logger import get_logger

logger = get_logger(__name__)


TAG_SYNONYMS: Dict[str, List[str]] = {
    "Womens": ["woman", "womans", "women", "womens", "aerie","aritzia", "ladies", "lady", "female", "her", "w"],
    "Mens": ["man", "mans", "men", "mens", "guys", "guy", "male", "him", "m"],
    "Kids": ["kid", "kids", "children", "child", "youth", "junior", "juniors", "boys", "girls", "baby", "babies", "toddler", "toddlers", "infant", "infants"],
    "Unisex": ["unisex", "all-gender", "gender-neutral", "genderless"],
    
    "Tops": ["top", "tops", "shirt", "shirts", "blouse", "blouses"],
    "T-Shirts": ["t-shirt", "t-shirts", "tshirt", "tshirts", "tee", "tees", "t shirt", "t shirts"],
    "Bottoms": ["bottom", "bottoms", "pant", "pants", "trouser", "trousers"],
    "Jeans": ["jean", "jeans", "denim", "denims"],
    "Shorts": ["short", "shorts"],
    "Skirts": ["skirt", "skirts"],
    "Dresses": ["dress", "dresses", "gown", "gowns", "frock", "frocks", "romper", "rompers", "jumpsuit", "jumpsuits"],
    "Outerwear": ["outerwear", "jacket", "jackets", "coat", "coats", "blazer", "blazers", "parka", "parkas"],
    "Sweaters": ["sweater", "sweaters", "jumper", "jumpers", "pullover", "pullovers", "cardigan", "cardigans", "hoodie", "hoodies", "sweatshirt", "sweatshirts"],
    "Activewear": ["activewear", "athletic", "athletics", "sport", "sports", "workout", "gym", "fitness", "athleisure"],
    "Swimwear": ["swimwear", "swim", "swimsuit", "swimsuits", "bikini", "bikinis"],
    "Underwear": ["underwear", "intimates", "lingerie", "bra", "bras", "panties", "boxers", "briefs"],
    "Sleepwear": ["sleepwear", "pajamas", "pyjamas", "loungewear", "nightwear", "robe", "robes"],
    "Shoes": ["shoe", "shoes", "footwear", "sneaker", "sneakers", "boot", "boots", "sandal", "sandals", "heel", "heels", "flat", "flats", "loafer", "loafers"],
    "Accessories": ["accessory", "accessories", "acc", "accs", "belt", "belts", "hat", "hats", "scarf", "scarves", "gloves", "sunglasses", "watch", "watches", "jewelry", "jewellery"],
    "Bags": ["bag", "bags", "purse", "purses", "handbag", "handbags", "tote", "totes", "backpack", "backpacks", "wallet", "wallets", "clutch", "clutches"],
    
    "New Arrivals": ["new-arrivals", "new arrivals", "newarrivals", "new", "just-in", "just in", "whats-new", "what's new", "latest", "fresh-picks"],
    "Sale": ["sale", "sales", "clearance", "discount", "discounts", "outlet", "reduced", "markdown", "markdowns"],
    "Trending": ["trending", "trend", "trends", "popular", "best-sellers", "bestsellers", "best sellers", "hot", "top-rated", "favorites", "favourites"],
    "Workwear": ["workwear", "work", "office", "professional", "business", "career"],
    "Casual": ["casual", "everyday", "basics", "essentials"],
    "Formal": ["formal", "dressy", "evening", "occasion", "party", "wedding", "prom"],
    "Vacation": ["vacation", "resort", "travel", "holiday", "beach", "cruise"],
}

TAG_HIERARCHY: Dict[str, int] = {
    "Womens": 10, "Mens": 10, "Kids": 10, "Unisex": 10,
    
    "Tops": 20, "T-Shirts": 21, "Bottoms": 20, "Jeans": 21, "Shorts": 21,
    "Skirts": 21, "Dresses": 20, "Outerwear": 20, "Sweaters": 21,
    "Activewear": 20, "Swimwear": 20, "Underwear": 20, "Sleepwear": 20,
    "Shoes": 20, "Accessories": 20, "Bags": 20,
    
    "New Arrivals": 30, "Sale": 30, "Trending": 30, "Workwear": 30,
    "Casual": 30, "Formal": 30, "Vacation": 30,
}


class TagNormalizer:
    """
    Normalizes tags to ensure consistency across different stores.
    
    Handles:
    - Synonym resolution (e.g., "woman" -> "Womens")
    - Fuzzy matching for typos
    - Hierarchy ordering (gender -> category -> occasion)
    - Deduplication
    """
    
    def __init__(
        self,
        synonyms: Dict[str, List[str]] = None,
        hierarchy: Dict[str, int] = None,
        fuzzy_threshold: float = 0.85
    ):
        self.synonyms = synonyms or TAG_SYNONYMS
        self.hierarchy = hierarchy or TAG_HIERARCHY
        self.fuzzy_threshold = fuzzy_threshold
        
        self._synonym_lookup = self._build_synonym_lookup()
        self._canonical_tags = set(self.synonyms.keys())
    
    def _build_synonym_lookup(self) -> Dict[str, str]:
        """Build reverse lookup from synonym -> canonical tag."""
        lookup = {}
        for canonical, variants in self.synonyms.items():
            lookup[canonical.lower()] = canonical
            for variant in variants:
                lookup[variant.lower()] = canonical
        return lookup
    
    def _fuzzy_match(self, tag: str) -> Optional[str]:
        """
        Find the closest canonical tag using fuzzy matching.
        
        Args:
            tag: The tag to match
            
        Returns:
            The closest canonical tag if similarity >= threshold, else None
        """
        tag_lower = tag.lower()
        best_match = None
        best_ratio = 0.0
        
        for canonical in self._canonical_tags:
            ratio = SequenceMatcher(None, tag_lower, canonical.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = canonical
            
            for variant in self.synonyms.get(canonical, []):
                ratio = SequenceMatcher(None, tag_lower, variant.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = canonical
        
        if best_ratio >= self.fuzzy_threshold:
            logger.debug(f"Fuzzy matched '{tag}' -> '{best_match}' (ratio={best_ratio:.2f})")
            return best_match
        
        return None
    
    def normalize_tag(self, tag: str) -> Optional[str]:
        """
        Normalize a single tag to its canonical form.
        
        Args:
            tag: Raw tag string
            
        Returns:
            Canonical tag name, or None if no match found
        """
        if not tag or not tag.strip():
            return None
        
        tag = tag.strip()
        tag_lower = tag.lower()
        
        if tag_lower in self._synonym_lookup:
            return self._synonym_lookup[tag_lower]
        
        if tag in self._canonical_tags:
            return tag
        
        fuzzy_result = self._fuzzy_match(tag)
        if fuzzy_result:
            return fuzzy_result
        
        logger.warning(f"Unknown tag '{tag}' could not be normalized")
        return None
    
    def normalize(self, tags: List[str]) -> List[str]:
        """
        Normalize a list of tags.
        
        Process:
        1. Normalize each tag to canonical form
        2. Remove duplicates (keeping first occurrence)
        3. Sort by hierarchy (gender -> category -> occasion)
        
        Args:
            tags: List of raw tag strings
            
        Returns:
            List of normalized, deduplicated, ordered tags
        """
        if not tags:
            return []
        
        normalized: Set[str] = set()
        seen_order: List[str] = []
        
        for tag in tags:
            canonical = self.normalize_tag(tag)
            if canonical and canonical not in normalized:
                normalized.add(canonical)
                seen_order.append(canonical)
        
        result = sorted(
            seen_order,
            key=lambda t: (self.hierarchy.get(t, 50), t)
        )
        
        logger.debug(f"Normalized tags {tags} -> {result}")
        return result
    
    def add_synonym(self, canonical: str, synonym: str) -> None:
        """
        Add a new synonym mapping.
        
        Args:
            canonical: The canonical tag name
            synonym: The synonym to add
        """
        if canonical not in self.synonyms:
            self.synonyms[canonical] = []
        
        if synonym.lower() not in [s.lower() for s in self.synonyms[canonical]]:
            self.synonyms[canonical].append(synonym)
            self._synonym_lookup[synonym.lower()] = canonical
            logger.info(f"Added synonym: '{synonym}' -> '{canonical}'")
    
    def get_all_canonical_tags(self) -> List[str]:
        """Get all canonical tag names, sorted by hierarchy."""
        return sorted(
            self._canonical_tags,
            key=lambda t: (self.hierarchy.get(t, 50), t)
        )
