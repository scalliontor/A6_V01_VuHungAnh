"""Compare V01 Vision ranking with V02 Vision + package OCR on held-out photos."""
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from application.image_service import ImageService
from application.order_service import OrderService
from application.ranking_service import RankingService
from application.search_service import SearchService
from data.order_repository import OrderRepository
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from presentation.search_ui import SearchUI


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/openfoodfacts"
TOP_K = 5
CALIBRATION_SIZE = 20
RANDOM_SEED = 20261007
WEIGHT_CANDIDATES = [i / 10 for i in range(0, 9)]


def ranked_ids(case, ocr_weight):
    return sorted(
        case["vision_scores"],
        key=lambda product_id: (
            -((1 - ocr_weight) * case["vision_scores"][product_id]
              + ocr_weight * case["package_scores"][product_id]),
            product_id,
        ),
    )[:TOP_K]


def summary(cases, weight):
    hits1 = hits5 = 0
    for case in cases:
        results = ranked_ids(case, weight)
        hits1 += bool(results and results[0] == case["expected_product_id"])
        hits5 += case["expected_product_id"] in results
    count = len(cases)
    return {
        "queries": count,
        "top1_hits": hits1,
        "top1_rate": round(hits1 / count, 4) if count else None,
        "top5_hits": hits5,
        "top5_rate": round(hits5 / count, 4) if count else None,
    }


def result_cases(cases, weight):
    output = []
    for case in cases:
        ids = ranked_ids(case, weight)
        output.append({
            key: case[key] for key in
            ("query_id", "query_image", "expected_product_id", "expected_product_name")
        } | {
            "ranked_product_ids": ids,
            "first_product_name": case["products"][ids[0]]["name"] if ids else None,
            "top1_success": bool(ids and ids[0] == case["expected_product_id"]),
            "top5_success": case["expected_product_id"] in ids,
        })
    return output


def main():
    repository = ProductRepository(DATA_DIR / "products.json")
    vector_index = VectorIndex(repository)
    ui = SearchUI(
        SearchService(repository, vector_index), ImageService(),
        OrderService(OrderRepository()),
    )
    queries = json.loads((DATA_DIR / "image_queries.json").read_text(encoding="utf-8"))
    products = {str(product["id"]): product for product in repository.all_products()}
    cases = []
    try:
        for number, item in enumerate(queries, 1):
            query_image = DATA_DIR / item["query_image"]
            # Exercise the same SearchUI and services used by the browser.
            _, actual_results = ui.image(query_image)
            vision_scores = dict(vector_index.last_image_scores)
            recognized_text = vector_index.last_ocr_text
            expected_id = str(item["expected_product_id"])
            expected = products[expected_id]
            package_scores = {
                product_id: SearchService.package_text_score(recognized_text, product)
                for product_id, product in products.items()
            }
            cases.append({
                "query_id": item["query_id"],
                "query_image": item["query_image"],
                "expected_product_id": expected_id,
                "expected_product_name": expected["name"],
                "vision_scores": vision_scores,
                "package_scores": package_scores,
                "products": products,
            })
            if number % 20 == 0:
                print(f"Processed {number}/{len(queries)} alternate-view photos", flush=True)
    finally:
        vector_index.close()

    shuffled = list(cases)
    random.Random(RANDOM_SEED).shuffle(shuffled)
    calibration = shuffled[:CALIBRATION_SIZE]
    test = shuffled[CALIBRATION_SIZE:]
    sweep = []
    for weight in WEIGHT_CANDIDATES:
        measured = summary(calibration, weight)
        sweep.append({"package_text_weight": weight, **measured})
    # Choose top-1 first, then top-5; if tied, prefer less OCR influence.
    selected = max(sweep, key=lambda row: (
        row["top1_hits"], row["top5_hits"], -row["package_text_weight"]
    ))["package_text_weight"]

    output = {
        "protocol": {
            "dataset": "Open Food Facts random-modulo-1000 product sample",
            "gallery_products": len(products),
            "alternate_view_queries": len(queries),
            "correct_match": "Same barcode as the query photo, using another view in the gallery",
            "calibration_queries": CALIBRATION_SIZE,
            "held_out_test_queries": len(test),
            "split_seed": RANDOM_SEED,
            "weight_selection": "Choose highest calibration top-1, then top-5; prefer lower OCR weight if tied",
            "apple_vision_score": "1 / (1 + Vision feature-print distance)",
            "package_text_score": "0.8 x product-name token coverage + 0.2 x brand-token match from Vision OCR",
            "source_manifest": json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8")),
        },
        "calibration_sweep": sweep,
        "selected_package_text_weight": selected,
        "v01_vision_baseline": {
            "held_out_summary": summary(test, 0.0),
            "held_out_cases": result_cases(test, 0.0),
        },
        "v02_vision_plus_package_ocr": {
            "held_out_summary": summary(test, selected),
            "held_out_cases": result_cases(test, selected),
        },
    }
    target = ROOT / "demo/v02_openfoodfacts_evaluation.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "calibration_selected_package_text_weight": selected,
        "v01_held_out_test": output["v01_vision_baseline"]["held_out_summary"],
        "v02_held_out_test": output["v02_vision_plus_package_ocr"]["held_out_summary"],
    }, indent=2))
    print(f"Saved {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
