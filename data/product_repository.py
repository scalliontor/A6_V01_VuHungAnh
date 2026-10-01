"""Load product records; the application layer never reads the JSON directly."""
import json
from pathlib import Path


class ProductRepository:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).with_name("products.json")
        self.products = json.loads(self.path.read_text(encoding="utf-8"))
        self.by_id = {product["id"]: product for product in self.products}
        if len(self.by_id) != len(self.products):
            raise ValueError("Duplicate product ID")

    def all_products(self):
        return list(self.products)

    def get(self, product_id):
        return self.by_id.get(product_id)

    def image_path(self, product):
        return self.path.parent / product["image"] if product.get("image") else None
