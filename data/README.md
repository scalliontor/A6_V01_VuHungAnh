# Data folders

Download and extract the real dataset using the commands in the project-root `README.md` before running the browser demonstration or real-photo evaluation.

This project contains two separate data sets:

| Location | Contents | Used for |
|---|---|---|
| `products.json`, `orders.json` | A small, manually designed catalog of 12 products and three sample orders. No artificial product images are included. | The quick text, voice-transcript, and order demonstration in `main.py`, plus small functional checks. |
| `openfoodfacts/` | 500 real product records, 500 front photos, and 100 different-view query photos. | The browser's text, voice-transcript, image, and combined search; also the real-photo evaluation. The same Python search classes and Apple Vision method are used. |

Inside `openfoodfacts/`, `products.json` lists the 500 catalog products, `image_queries.json` lists the 100 held-out queries, and `images/` contains their photos. See `openfoodfacts/DATASET.md` for the original source, selection method, and license; see `openfoodfacts/manifest.json` for the source URL and SHA-256. The raw source export is not needed to rerun the included evaluation.

**Labels used:** every selected product has an ID/barcode and title; 350 of 500 have a brand; 204 of 500 have a usable broad category. Each held-out image query has the expected product barcode. Of the 100 image queries, 52 have a usable broad category for the optional category-level check. Missing and `undefined` categories are excluded from that check.

Open Food Facts does not supply shop prices or inventory for this task. The converted records therefore use `price: null`, `stock: 1`, and `popularity: 0.5` as schema placeholders. The real-photo image test ranks by Apple Vision similarity, so these placeholders do not affect its image ranking.

Saved evaluation results are in `../demo/openfoodfacts_evaluation.json`.
