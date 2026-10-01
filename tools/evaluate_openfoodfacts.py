"""Evaluate the submitted Python + Apple Vision search application on real photos."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from application.image_service import ImageService
from application.order_service import OrderService
from application.search_service import SearchService
from data.order_repository import OrderRepository
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from presentation.search_ui import SearchUI


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/openfoodfacts"
TOP_K = 5


def summary(cases):
    count = len(cases)
    first = sum(case["top1_success"] for case in cases)
    first_five = sum(case["top5_success"] for case in cases)
    return {
        "queries": count,
        "top1_hits": first,
        "top1_rate": round(first / count, 4) if count else None,
        "top5_hits": first_five,
        "top5_rate": round(first_five / count, 4) if count else None,
    }


def main():
    repository = ProductRepository(DATA_DIR / "products.json")
    image_service = ImageService()
    ui = SearchUI(
        SearchService(repository, VectorIndex(repository)),
        image_service,
        OrderService(OrderRepository()),
    )
    queries = json.loads((DATA_DIR / "image_queries.json").read_text(encoding="utf-8"))
    products = {str(product["id"]): product for product in repository.all_products()}
    image_cases = []
    text_cases = []
    category_cases = []
    skipped_category = 0

    try:
        for item in queries:
            expected_id = str(item["expected_product_id"])
            expected = products[expected_id]
            _, image_results = ui.image(DATA_DIR / item["query_image"])
            image_ids = [str(result["product"]["id"]) for result in image_results]
            image_cases.append({
                "query_id": item["query_id"],
                "query_image": item["query_image"],
                "expected_product_id": expected_id,
                "expected_product_name": expected["name"],
                "first_product_name": image_results[0]["product"]["name"] if image_results else None,
                "ranked_product_ids": image_ids,
                "top1_success": bool(image_ids and image_ids[0] == expected_id),
                "top5_success": expected_id in image_ids[:TOP_K],
            })

            category = expected.get("category_root")
            if category and category != "undefined":
                category_matches = [products[product_id].get("category_root") == category
                                    for product_id in image_ids]
                category_cases.append({
                    "query_id": item["query_id"],
                    "category": category,
                    "top1_success": bool(category_matches and category_matches[0]),
                    "top5_success": any(category_matches[:TOP_K]),
                })
            else:
                skipped_category += 1

            # The exact indexed title is an intentionally easy lexical query.
            _, text_results = ui.text(expected["name"])
            text_ids = [str(result["product"]["id"]) for result in text_results]
            text_cases.append({
                "query_id": item["query_id"],
                "query": expected["name"],
                "expected_product_id": expected_id,
                "ranked_product_ids": text_ids,
                "top1_success": bool(text_ids and text_ids[0] == expected_id),
                "top5_success": expected_id in text_ids[:TOP_K],
            })
    finally:
        ui.search_service.vector_index.close()

    output = {
        "protocol": {
            "dataset": "Open Food Facts random-modulo-1000 product sample",
            "method": "Submitted SearchUI/SearchService with local Apple Vision feature prints",
            "gallery_products": len(products),
            "alternate_view_queries": len(queries),
            "top_k": TOP_K,
            "correct_exact_match": "Same barcode as the query photo, using another view in the gallery",
            "category_label": "Same broadest available Open Food Facts category tag",
            "text_query": "The catalog's own exact product title",
            "source_manifest": json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8")),
        },
        "image_search": {"summary": summary(image_cases), "cases": image_cases},
        "image_category_search": {
            "summary": {**summary(category_cases), "unlabeled_queries_excluded": skipped_category},
            "cases": category_cases,
        },
        "text_search": {"summary": summary(text_cases), "cases": text_cases},
    }
    target = ROOT / "demo/openfoodfacts_evaluation.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: output[name]["summary"] for name in
                      ("image_search", "image_category_search", "text_search")}, indent=2))
    print(f"Saved {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
