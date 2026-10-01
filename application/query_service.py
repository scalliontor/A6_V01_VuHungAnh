"""Normalize product inputs and extract explicit catalog constraints."""
import re
from pathlib import Path
from application.text_normalization import fold_accents


STOP_WORDS = {
    "find", "show", "me", "products", "product", "please", "a", "an", "the",
    "dollars", "dollar", "under", "below", "less", "than", "with", "for", "t",
}

CATEGORY_ALIASES = {
    "shoes": ("shoes", "shoe", "sneakers", "sneaker", "trainers", "trainer"),
    "shirt": ("t shirts", "t shirt", "tee shirts", "tee shirt", "shirts", "shirt", "tees", "tee"),
    "bag": ("bags", "bag", "backpacks", "backpack"),
    "headphones": ("headphones", "headphone", "headset", "headsets"),
    "bottle": ("water bottles", "water bottle", "bottles", "bottle"),
    "watch": ("watches", "watch"),
}

TOKEN_ALIASES = {
    "shoe": "shoes", "sneaker": "shoes", "sneakers": "shoes",
    "trainer": "shoes", "trainers": "shoes", "shirts": "shirt",
    "tees": "shirt", "tee": "shirt", "bags": "bag",
    "headphone": "headphones", "headsets": "headphones", "headset": "headphones",
    "bottles": "bottle", "watches": "watch",
}
COLOR_TERMS = {
    "black", "white", "gray", "grey", "blue", "red", "green", "yellow", "orange",
    "purple", "pink", "brown", "silver", "gold", "navy", "beige",
}


class QueryService:
    def __init__(self, products=()):
        self.colors = COLOR_TERMS | {
            fold_accents(product["color"]) for product in products if product.get("color")
        }
        self.brands = {fold_accents(product["brand"]) for product in products if product.get("brand")}

    @staticmethod
    def _contains_phrase(text, phrase):
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in phrase.split()) + r"\b"
        return re.search(pattern, text) is not None

    def text_query(self, text):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text query is empty")
        folded = fold_accents(text)
        normalized = re.sub(r"[^a-z0-9]+", " ", folded).strip()
        maximum = re.search(r"\b(?:under|below|less than)\s*\$?\s*(\d+(?:\.\d+)?)", folded)
        cleaned = re.sub(r"\b(?:under|below|less than)\s*\$?\s*\d+(?:\.\d+)?(?:\s*dollars?)?\b", " ", normalized)

        category = None
        aliases = sorted(
            ((alias, value) for value, names in CATEGORY_ALIASES.items() for alias in names),
            key=lambda pair: len(pair[0].split()), reverse=True,
        )
        for alias, value in aliases:
            if self._contains_phrase(cleaned, alias):
                category = value
                break

        words = re.findall(r"[a-z0-9]+", cleaned)
        color = next((word for word in words if word in self.colors), None)
        brand = next((word for word in words if word in self.brands), None)
        tokens = [TOKEN_ALIASES.get(word, word) for word in words if word not in STOP_WORDS]
        return {
            "type": "text", "raw": text, "tokens": tokens,
            "category": category, "color": color, "brand": brand,
            "max_price": float(maximum.group(1)) if maximum else None,
            "image_path": None,
        }

    def voice_query(self, transcript):
        query = self.text_query(transcript)
        query["type"] = "voice"
        return query

    def image_query(self, image_path):
        return {
            "type": "image", "raw": Path(image_path).name, "tokens": [],
            "category": None, "color": None, "brand": None,
            "max_price": None, "image_path": str(Path(image_path).resolve()),
        }

    def multimodal_query(self, text, image_path):
        query = self.text_query(text)
        query.update(type="multimodal", image_path=str(Path(image_path).resolve()))
        return query
