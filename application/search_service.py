"""Retrieve candidates, then hand them to RankingService."""
import re
from application.ranking_service import RankingService
from application.text_normalization import fold_accents


class SearchService:
    def __init__(self, repository, vector_index, ranking_service=None):
        self.repository = repository
        self.vector_index = vector_index
        self.ranking = ranking_service or RankingService()

    def query_metadata(self):
        """Return only catalog attributes needed for query constraint parsing."""
        return [{"color": product["color"], "brand": product["brand"]}
                for product in self.repository.all_products()]

    @staticmethod
    def text_score(tokens, product):
        if not tokens:
            return 0.0
        name = fold_accents(product["name"]).split()
        metadata = fold_accents(product["category"] + " " + product["brand"] + " " + product["color"]
                                + " " + product["description"]).split()
        matched = sum(1.0 if token in name else 0.55 if token in metadata else 0.0 for token in tokens)
        return matched / len(tokens)

    @staticmethod
    def package_text_score(recognized_text, product):
        """Measure how much of a product's identifying name appears in package OCR."""
        if not recognized_text:
            return 0.0
        stop_words = {"and", "the", "for", "with", "of", "in", "a", "an"}

        def tokens(value):
            return {token for token in re.findall(r"[a-z0-9]+", fold_accents(value))
                    if len(token) > 1 and token not in stop_words}

        observed = tokens(recognized_text)
        name = tokens(product["name"])
        brand = tokens(product.get("brand") or "")
        if not name:
            return 0.0
        name_coverage = len(name & observed) / len(name)
        brand_match = bool(brand & observed)
        return 0.8 * name_coverage + 0.2 * float(brand_match)

    def search(self, query, top_k=5):
        if query["type"] not in {"text", "voice", "image", "multimodal"}:
            raise ValueError("Unsupported query type")
        image_scores = self.vector_index.scores(query["image_path"]) if query.get("image_path") else {}
        recognized_text = getattr(self.vector_index, "last_ocr_text", "")
        candidates = []
        for product in self.repository.all_products():
            if query["max_price"] is not None and (
                product["price"] is None or product["price"] >= query["max_price"]
            ):
                continue
            if query.get("category") and product["category"].casefold() != query["category"]:
                continue
            if query.get("color") and product["color"].casefold() != query["color"]:
                continue
            if query.get("brand") and product["brand"].casefold() != query["brand"]:
                continue
            text = self.text_score(query["tokens"], product)
            image = image_scores.get(str(product["id"]), 0.0)
            package_text = self.package_text_score(recognized_text, product)
            if query["type"] in {"text", "voice"} and text == 0:
                continue
            candidates.append({"product": product, "text_score": text, "image_score": image,
                               "package_text_score": package_text})
        return self.ranking.rank(candidates, query["type"])[:top_k]

    def view_product(self, product_id):
        return self.repository.get(product_id)
