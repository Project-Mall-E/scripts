from dataclasses import dataclass

@dataclass
class Product:
    store: str
    item_name: str
    item_image_link: str
    item_link: str
    price: str
    tags: list[str]