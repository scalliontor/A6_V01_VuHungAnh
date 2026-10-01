"""Create a deterministic, license-attributed OFF image-retrieval benchmark.

The source archive is the official 1-in-1,000 product metadata sample. This
script keeps a 500-product gallery and up to 100 held-out alternate views. It
downloads only the selected 400px images, not the full multi-gigabyte image dump.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
import posixpath
from pathlib import Path
import sys
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/openfoodfacts"
ARCHIVE = DATA_DIR / "products.random-modulo-1000.tar.gz"
PRODUCTS_OUT = DATA_DIR / "products.json"
QUERIES_OUT = DATA_DIR / "image_queries.json"
IMAGES_DIR = DATA_DIR / "images"
GALLERY_LIMIT = 500
QUERY_LIMIT = 100
USER_AGENT = "Assignment06-V01-educational-evaluation/1.0"


def _stable_key(code):
    return sha256(f"assignment06-v01-openfoodfacts:{code}".encode()).hexdigest()


def _english_name(row):
    name = row.get("product_name_en")
    if not name and "en" in (row.get("languages_codes") or []):
        name = row.get("product_name")
    if not isinstance(name, str) or not name.strip():
        return None
    letters = [character for character in name if character.isalpha()]
    if not letters or any("LATIN" not in unicodedata.name(character, "") for character in letters):
        return None
    return " ".join(name.split())


def _image_path(code):
    barcode = str(code).strip()
    if not barcode.isdigit():
        return None
    barcode = barcode.zfill(13)
    return "/".join((barcode[:3], barcode[3:6], barcode[6:9], barcode[9:]))


def _image_filename(key, image_meta):
    sizes = image_meta.get("sizes") or {}
    resolution = "400" if "400" in sizes else "200" if "200" in sizes else None
    if not resolution:
        return None
    if key.isdigit():
        return f"{key}.{resolution}.jpg"
    revision = image_meta.get("rev")
    return f"{key}.{revision}.{resolution}.jpg" if revision is not None else None


def _select_images(row):
    images = row.get("images") or {}
    uploaded = images.get("uploaded") if isinstance(images.get("uploaded"), dict) else {}
    selected_fronts = (images.get("selected") or {}).get("front") or {}
    if selected_fronts:
        locales = sorted(selected_fronts, key=lambda locale: (locale != "en", locale))
        front_locale = locales[0]
        fronts = [(f"front_{front_locale}", selected_fronts[front_locale])]
    else:
        fronts = [(key, value) for key, value in images.items()
                  if isinstance(key, str) and key.startswith("front_") and isinstance(value, dict)]
        fronts.sort(key=lambda pair: (pair[0] != "front_en", pair[0]))
    if not fronts:
        return None
    front_key, front_meta = fronts[0]
    front_filename = _image_filename(front_key, front_meta)
    code_path = _image_path(row.get("code", row.get("_id", "")))
    if not front_filename or not code_path:
        return None

    front_source_id = str(front_meta.get("imgid", ""))
    alternates = []
    raw_images = uploaded or images
    for key, value in raw_images.items():
        if key.isdigit() and key != front_source_id and _image_filename(key, value):
            alternates.append((key, value))
    # Prefer a separate raw photograph, which is an actual alternate view of
    # the same barcode, over nutrition/ingredients crops derived from it.
    alternates.sort(key=lambda pair: (int(pair[0]), pair[0]))
    if not alternates:
        return {"path": code_path, "front": front_filename, "alternate": None}
    alt_key, alt_meta = alternates[0]
    return {
        "path": code_path,
        "front": front_filename,
        "alternate": _image_filename(alt_key, alt_meta),
        "alternate_key": alt_key,
    }


def _load_rows(archive_path):
    import tarfile

    rows = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            if (not member.name.endswith("/product.json") or member.name.startswith("invalid/")):
                continue
            target = member
            if member.issym():
                # The official Mongo dump packages product.json as a relative
                # symlink to the newest numeric revision in the same folder.
                directory = posixpath.dirname(member.name)
                target_name = posixpath.normpath(posixpath.join(directory, member.linkname))
                if not target_name.startswith(directory + "/") or ".." in member.linkname.split("/"):
                    continue
                try:
                    target = archive.getmember(target_name)
                except KeyError:
                    continue
            if not target.isfile():
                continue
            source = archive.extractfile(target)
            if source is None:
                continue
            try:
                row = json.load(source)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            code = str(row.get("code") or row.get("_id") or "").strip()
            name = _english_name(row)
            selected = _select_images(row)
            if code and name and selected:
                row["_benchmark_code"] = code
                row["_benchmark_name"] = name
                row["_benchmark_images"] = selected
                rows.append(row)
    return rows


def _download_one(code, code_path, filename, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            with Image.open(destination) as image:
                image.verify()
            return destination, None
        except Exception:
            destination.unlink(missing_ok=True)
    relative = f"data/{code_path}/{filename}"
    urls = (
        f"https://openfoodfacts-images.s3.eu-west-3.amazonaws.com/{relative}",
        f"https://images.openfoodfacts.org/images/products/{code_path}/{filename}",
    )
    errors = []
    for url in urls:
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=35) as response:
                content = response.read()
            destination.write_bytes(content)
            with Image.open(destination) as image:
                image.verify()
            return destination, None
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            errors.append(f"{url}: {error}")
            destination.unlink(missing_ok=True)
    return destination, "; ".join(errors)


def _product_record(row, front_file):
    categories = row.get("categories_tags") or []
    category = categories[-1].removeprefix("en:").replace("-", " ") if categories else "food product"
    category_root = categories[0].removeprefix("en:").replace("-", " ") if categories else None
    description = row.get("generic_name_en") or ""
    brand = row.get("brands") or ""
    filename = front_file.name
    return {
        "id": str(row["_benchmark_code"]),
        "name": row["_benchmark_name"],
        "category": category,
        "category_root": category_root,
        "brand": str(brand).split(",")[0].strip(),
        "color": "",
        "price": None,
        "stock": 1,
        "popularity": 0.5,
        "description": str(description)[:400],
        "image": f"images/{filename}",
        "source": "Open Food Facts",
    }


def main():
    if not ARCHIVE.exists():
        raise SystemExit(
            f"Missing {ARCHIVE}. Download the official sample archive first; see DATASET.md."
        )
    rows = _load_rows(ARCHIVE)
    rows.sort(key=lambda row: _stable_key(row["_benchmark_code"]))
    queryable = [row for row in rows if row["_benchmark_images"].get("alternate")]
    query_rows = queryable[:QUERY_LIMIT]
    gallery_by_code = {row["_benchmark_code"]: row for row in query_rows}
    for row in rows:
        if len(gallery_by_code) >= GALLERY_LIMIT:
            break
        gallery_by_code.setdefault(row["_benchmark_code"], row)
    gallery_rows = list(gallery_by_code.values())
    gallery_rows.sort(key=lambda row: row["_benchmark_code"])

    requests = []
    destinations = {}
    for row in gallery_rows:
        code = row["_benchmark_code"]
        selected = row["_benchmark_images"]
        front_dest = IMAGES_DIR / f"{code}_front.jpg"
        requests.append((code, selected["path"], selected["front"], front_dest))
        destinations[(code, "front")] = front_dest
    for row in query_rows:
        code = row["_benchmark_code"]
        selected = row["_benchmark_images"]
        alt_dest = IMAGES_DIR / f"{code}_query.jpg"
        requests.append((code, selected["path"], selected["alternate"], alt_dest))
        destinations[(code, "query")] = alt_dest

    errors = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {
            pool.submit(_download_one, code, path, filename, destination): destination
            for code, path, filename, destination in requests
        }
        for future in as_completed(futures):
            result_path, error = future.result()
            if error:
                errors.append({"path": str(result_path.relative_to(ROOT)), "error": error})

    products = []
    successful_codes = set()
    for row in gallery_rows:
        code = row["_benchmark_code"]
        front_file = destinations[(code, "front")]
        if front_file.is_file() and front_file.stat().st_size > 0:
            products.append(_product_record(row, front_file))
            successful_codes.add(code)
    queries = []
    for row in query_rows:
        code = row["_benchmark_code"]
        query_file = destinations[(code, "query")]
        if code in successful_codes and query_file.is_file() and query_file.stat().st_size > 0:
            queries.append({
                "query_id": f"off-{code}",
                "expected_product_id": code,
                "query_image": f"images/{query_file.name}",
                "product_name": row["_benchmark_name"],
                "alternate_image_key": row["_benchmark_images"]["alternate_key"],
            })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCTS_OUT.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n")
    QUERIES_OUT.write_text(json.dumps(queries, ensure_ascii=False, indent=2) + "\n")
    referenced_images = {IMAGES_DIR / Path(product["image"]).name for product in products}
    referenced_images.update(IMAGES_DIR / Path(query["query_image"]).name for query in queries)
    for image_path in IMAGES_DIR.glob("*.jpg"):
        if image_path not in referenced_images:
            image_path.unlink()
    archive_hash = sha256(ARCHIVE.read_bytes()).hexdigest()
    info = {
        "dataset": "Open Food Facts product database sample",
        "source_archive": "https://static.openfoodfacts.org/exports/products.random-modulo-1000.tar.gz",
        "archive_sha256": archive_hash,
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "source_products_with_english_name_and_front_image": len(rows),
        "gallery_products": len(products),
        "alternate_view_queries": len(queries),
        "gallery_limit": GALLERY_LIMIT,
        "query_limit": QUERY_LIMIT,
        "selection_seed": "assignment06-v01-openfoodfacts",
        "image_resolution": "400 px maximum; 200 px used if 400 px variant is absent",
        "download_errors": errors,
        "data_license": "Open Database License (ODbL) 1.0; Database Contents License 1.0",
        "image_license": "Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)",
    }
    (DATA_DIR / "manifest.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps({k: v for k, v in info.items() if k != "download_errors"}, indent=2))
    if errors:
        print(f"Image download failures: {len(errors)} (see {DATA_DIR / 'manifest.json'})", file=sys.stderr)


if __name__ == "__main__":
    main()
