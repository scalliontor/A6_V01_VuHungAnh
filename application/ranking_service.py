"""Rank retrieved products by text, Apple Vision distance, and package OCR."""


class RankingService:
    PACKAGE_TEXT_WEIGHT = 0.1

    def rank(self, candidates, query_type):
        weights = {"text": (0.9, 0.0, 0.0, 0.1), "voice": (0.9, 0.0, 0.0, 0.1),
                   "image": (0.0, 0.9, self.PACKAGE_TEXT_WEIGHT, 0.0),
                   "multimodal": (0.4, 0.4, self.PACKAGE_TEXT_WEIGHT, 0.1)}
        text_weight, image_weight, ocr_weight, business_weight = weights[query_type]
        for item in candidates:
            product = item["product"]
            business = 0.6 * product["popularity"] + 0.4 * (1 if product["stock"] > 0 else 0)
            item["business_score"] = round(business, 4)
            ranking_score = (text_weight * item["text_score"] + image_weight * item["image_score"]
                             + ocr_weight * item.get("package_text_score", 0.0)
                             + business_weight * business)
            item["score"] = round(ranking_score, 4)
            item["_ranking_score"] = ranking_score
        ranked = sorted(candidates, key=lambda item: (-item["_ranking_score"], item["product"]["id"]))
        for item in ranked:
            del item["_ranking_score"]
        return ranked
