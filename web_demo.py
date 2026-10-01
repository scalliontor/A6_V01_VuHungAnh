"""Small local browser demonstration backed by the submitted search services."""
import argparse
import base64
import binascii
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from application.image_service import ImageService
from application.order_service import OrderService
from application.search_service import SearchService
from data.order_repository import OrderRepository
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from presentation.search_ui import SearchUI


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data/openfoodfacts"
WEB = ROOT / "web"
PHOTO_NAME = re.compile(r"[0-9]+_(?:front|query)\.jpg\Z")
UPLOAD = re.compile(r"data:image/(?:jpeg|png|webp);base64,([A-Za-z0-9+/=]+)\Z")
FEATURED_IDS = (
    "off-5010251561958",  # correct same-product match
    "off-9300633679965",
    "off-0055742578010",
    "off-01758979",       # difficult back-of-package example
)


def make_ui():
    repository = ProductRepository(DATA / "products.json")
    return SearchUI(
        SearchService(repository, VectorIndex(repository)),
        ImageService(),
        OrderService(OrderRepository()),
    )


def photo_url(relative_path):
    name = Path(relative_path).name
    return f"/photos/{name}" if PHOTO_NAME.fullmatch(name) else None


class DemoServer(HTTPServer):
    def __init__(self, address):
        super().__init__(address, DemoHandler)
        self.ui = make_ui()
        self.queries = json.loads((DATA / "image_queries.json").read_text(encoding="utf-8"))
        self.queries_by_id = {item["query_id"]: item for item in self.queries}
        self.products = self.ui.search_service.repository.all_products()
        self.products_by_id = {str(item["id"]): item for item in self.products}


class DemoHandler(BaseHTTPRequestHandler):
    server: DemoServer

    def log_message(self, format, *args):
        if self.path.startswith("/api/"):
            super().log_message(format, *args)

    def send_bytes(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8", status)

    def do_GET(self):
        request_path = urlsplit(self.path).path
        static = {
            "/": (WEB / "index.html", "text/html; charset=utf-8"),
            "/app.css": (WEB / "app.css", "text/css; charset=utf-8"),
            "/app.js": (WEB / "app.js", "text/javascript; charset=utf-8"),
        }
        if request_path in static:
            path, content_type = static[request_path]
            return self.send_bytes(path.read_bytes(), content_type)
        if request_path == "/api/meta":
            broad = Counter(item["category_root"] for item in self.server.products
                            if item.get("category_root") and item["category_root"] != "undefined")
            featured = [self.server.queries_by_id[key] for key in FEATURED_IDS]
            return self.send_json({
                "product_count": len(self.server.products),
                "query_count": len(self.server.queries),
                "brand_count": sum(bool(item.get("brand")) for item in self.server.products),
                "category_count": sum(bool(item.get("category_root")) and
                                      item["category_root"] != "undefined"
                                      for item in self.server.products),
                "categories": [{"label": name, "count": count}
                               for name, count in broad.most_common()],
                "featured_queries": [{
                    "id": item["query_id"], "name": item["product_name"],
                    "image": photo_url(item["query_image"]),
                    "barcode": item["expected_product_id"],
                } for item in featured],
            })
        if request_path.startswith("/photos/"):
            name = request_path.removeprefix("/photos/")
            if PHOTO_NAME.fullmatch(name):
                path = DATA / "images" / name
                if path.is_file():
                    return self.send_bytes(path.read_bytes(), "image/jpeg")
        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/api/search":
            return self.send_json({"error": "Not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 8_000_000:
                raise ValueError("Request is empty or too large (8 MB maximum)")
            payload = json.loads(self.rfile.read(length))
            result = self.search(payload)
            self.send_json(result)
        except (ValueError, KeyError, TypeError, OSError, binascii.Error) as error:
            self.send_json({"error": str(error)}, 400)

    def search(self, payload):
        mode = payload.get("mode")
        text = str(payload.get("text", "")).strip()
        sample = None
        temporary = None
        try:
            if mode in {"image", "multimodal"}:
                sample_id = payload.get("sample_id")
                upload = payload.get("upload")
                if upload:
                    match = UPLOAD.fullmatch(upload)
                    if not match:
                        raise ValueError("Upload a JPEG, PNG, or WebP photo")
                    raw = base64.b64decode(match.group(1), validate=True)
                    if len(raw) > 5_000_000:
                        raise ValueError("Image must be 5 MB or smaller")
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as handle:
                        handle.write(raw)
                        temporary = Path(handle.name)
                    image_path = temporary
                else:
                    sample = self.server.queries_by_id.get(sample_id)
                    if sample is None:
                        raise ValueError("Choose a sample photo or upload one")
                    image_path = DATA / sample["query_image"]
            if mode == "text":
                query, results = self.server.ui.text(text)
            elif mode == "voice":
                query, results = self.server.ui.voice(text)
            elif mode == "image":
                query, results = self.server.ui.image(image_path)
            elif mode == "multimodal":
                query, results = self.server.ui.multimodal(text, image_path)
            else:
                raise ValueError("Select a supported search mode")
            response = {
                "mode": mode,
                "query": {key: query.get(key) for key in
                          ("raw", "tokens", "category", "brand", "color", "max_price")},
                "results": [{
                    "id": str(row["product"]["id"]),
                    "name": row["product"]["name"],
                    "brand": row["product"].get("brand") or None,
                    "category": row["product"].get("category_root") or None,
                    "image": photo_url(row["product"]["image"]),
                    "score": round(row["score"], 4),
                    "text_score": round(row["text_score"], 4),
                    "image_score": round(row["image_score"], 4),
                } for row in results],
            }
            if sample:
                expected = self.server.products_by_id[sample["expected_product_id"]]
                response["sample_label"] = {
                    "barcode": sample["expected_product_id"],
                    "name": expected["name"],
                    "category": expected.get("category_root"),
                    "top1_match": bool(results and str(results[0]["product"]["id"]) ==
                                       sample["expected_product_id"]),
                }
            return response
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Open the local browser demonstration")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = DemoServer(("127.0.0.1", args.port))
    print(f"Open http://127.0.0.1:{server.server_port} in a browser", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.ui.search_service.vector_index.close()
        server.server_close()


if __name__ == "__main__":
    main()
