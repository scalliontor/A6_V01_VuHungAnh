"""Rank retrieved products; image-only order follows Vision distance."""


class RankingService:
    def rank(self, candidates, query_type):
        weights = {"text": (0.9, 0.0, 0.1), "voice": (0.9, 0.0, 0.1),
                   "image": (0.0, 1.0, 0.0), "multimodal": (0.45, 0.45, 0.1)}
        text_weight, image_weight, business_weight = weights[query_type]
        for item in candidates:
            product = item["product"]
            business = 0.6 * product["popularity"] + 0.4 * (1 if product["stock"] > 0 else 0)
            item["business_score"] = round(business, 4)
            ranking_score = (text_weight * item["text_score"] + image_weight * item["image_score"]
                             + business_weight * business)
            item["score"] = round(ranking_score, 4)
            item["_ranking_score"] = ranking_score
        ranked = sorted(candidates, key=lambda item: (-item["_ranking_score"], item["product"]["id"]))
        for item in ranked:
            del item["_ranking_score"]
        return ranked
