"""Run the fixed, labeled retrieval and order-search evaluation suite."""
import json
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import create_ui


ROOT = Path(__file__).resolve().parents[1]
K = 5

# Relevance is a set because broad queries can have more than one correct item.
PRODUCT_CASES = [
    {"mode": "text", "input": "Nike shoes under 100 dollars", "relevant_ids": [1]},
    {"mode": "text", "input": "black leather bag", "relevant_ids": [5]},
    {"mode": "text", "input": "green water bottle", "relevant_ids": [11]},
    {"mode": "text", "input": "silver wireless headphones", "relevant_ids": [9]},
    {"mode": "text", "input": "blue sports shirt", "relevant_ids": [7]},
    {"mode": "text", "input": "sneakers", "relevant_ids": [1, 2, 3, 4]},
    {"mode": "text", "input": "red headphones", "relevant_ids": [10]},
    {"mode": "text", "input": "brown backpack under 70", "relevant_ids": [6]},
    {"mode": "text", "input": "puma blue sneakers", "relevant_ids": [3]},
    {"mode": "text", "input": "black products", "relevant_ids": [1, 5, 8, 12]},
    {"mode": "text", "input": "red running shoes", "relevant_ids": [4]},
    {"mode": "text", "input": "t-shirts", "relevant_ids": [7, 8]},
    {"mode": "text", "input": "running shoes under 100", "relevant_ids": [1, 2]},
    {"mode": "text", "input": "Nike shoes under 90", "relevant_ids": []},
    {"mode": "text", "input": "red water bottle", "relevant_ids": []},
    {"mode": "text", "input": "purple backpack", "relevant_ids": []},
    {"mode": "voice", "input": "find black running shoes", "relevant_ids": [1]},
    {"mode": "voice", "input": "show me blue cotton shirt", "relevant_ids": [7]},
    {"mode": "voice", "input": "find sneakers under 90", "relevant_ids": [2, 3]},
]

ORDER_CASES = [
    {"customer_id": "C001", "input": "find my order 20261001", "relevant_id": "20261001"},
    {"customer_id": "C001", "input": "where is my latest order?", "relevant_id": "20261001"},
    {"customer_id": "C002", "input": "find my order 20261001", "relevant_id": None},
    {"customer_id": "C001", "input": "find my order O999", "relevant_id": None},
]


def _ids(results):
    return [item["product"]["id"] for item in results]


def _product_case(ui, case):
    mode, value = case["mode"], case["input"]
    query, results = getattr(ui, mode)(value)

    relevant = set(case["relevant_ids"])
    ranked_ids = _ids(results)
    if relevant:
        success = bool(ranked_ids and ranked_ids[0] in relevant)
    else:
        success = not ranked_ids

    return {
        "mode": mode, "input": value, "normalized_query": {
            "tokens": query["tokens"], "category": query.get("category"),
            "color": query.get("color"), "brand": query.get("brand"),
            "max_price": query["max_price"],
        },
        "relevant_ids": sorted(relevant), "ranked_ids": ranked_ids,
        "ranked_results": [{"id": item["product"]["id"], "name": item["product"]["name"],
                             "score": item["score"]} for item in results],
        "success": success,
    }


def _metrics(rows):
    positive = [row for row in rows if row["relevant_ids"]]
    negative = [row for row in rows if not row["relevant_ids"]]
    return {
        "queries": len(rows),
        "positive_queries": len(positive),
        "top1_hits": sum(row["success"] for row in positive),
        "top1_accuracy": round(sum(row["success"] for row in positive) / len(positive), 4) if positive else None,
        "negative_queries": len(negative),
        "correct_no_match": sum(row["success"] for row in negative),
        "all_case_successes": sum(row["success"] for row in rows),
        "all_case_success_rate": round(sum(row["success"] for row in rows) / len(rows), 4) if rows else None,
    }


def main():
    ui = create_ui()
    product_rows = [_product_case(ui, case) for case in PRODUCT_CASES]
    grouped = defaultdict(list)
    for row in product_rows:
        grouped[row["mode"]].append(row)

    order_rows = []
    for case in ORDER_CASES:
        result = ui.order_text(case["customer_id"], case["input"])
        actual = result["order_id"] if result else None
        order_rows.append({**case, "actual_id": actual, "status": result["status"] if result else None,
                           "success": actual == case["relevant_id"]})

    summary = {
        "evaluation_protocol": {
            "catalog_size": len(ui.search_service.repository.all_products()),
            "top_k": K,
            "relevance": "Manually labeled product-ID sets; broad queries may have multiple relevant products.",
            "success": "The first result is relevant, or an expected no-match query returns no products.",
            "limitations": "Text and simulated voice only on a small synthetic catalog; real-photo image search is evaluated separately on Open Food Facts.",
        },
        "product_search": {
            "overall": _metrics(product_rows),
            "by_mode": {mode: _metrics(rows) for mode, rows in sorted(grouped.items())},
            "cases": product_rows,
        },
        "order_lookup": {
            "queries": len(order_rows),
            "successful": sum(row["success"] for row in order_rows),
            "accuracy": round(sum(row["success"] for row in order_rows) / len(order_rows), 4),
            "cases": order_rows,
        },
    }
    output = json.dumps(summary, indent=2) + "\n"
    (ROOT / "demo/evaluation.json").write_text(output)
    print(output, end="")


if __name__ == "__main__":
    main()
