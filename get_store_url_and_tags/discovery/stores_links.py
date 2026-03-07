from dataclasses import dataclass
from typing import List

@dataclass
class StoreLink:
    name: str
    url: str
    tags: List[str]
