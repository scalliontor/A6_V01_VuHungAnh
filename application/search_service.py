"""Retrieve candidates, then hand them to RankingService."""
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

    def search(self, query, top_k=5):
        if query["type"] not in {"text", "voice", "image", "multimodal"}:
            raise ValueError("Unsupported query type")
        image_scores = self.vector_index.scores(query["image_path"]) if query.get("image_path") else {}
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
            if query["type"] in {"text", "voice"} and text == 0:
                continue
            candidates.append({"product": product, "text_score": text, "image_score": image})
        return self.ranking.rank(candidates, query["type"])[:top_k]

    def view_product(self, product_id):
        return self.repository.get(product_id)
