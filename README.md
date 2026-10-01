# Assignment 06 — Multimodal E-Commerce Search

**Student:** Vu Hung Anh — B23DCDT022

**Submission date:** 1 October 2026

**Version:** V01

**Report language:** English

**Source repository:** https://github.com/scalliontor/A6_V01_VuHungAnh

**Prepared dataset:** https://drive.google.com/drive/folders/1Ta9vMurnYoJzvNcP23Iflulr-EVWIx58

## Submission contents

| Item | Location | Description |
|---|---|---|
| Report | report/assignment06_report.pdf | Requirements, UML models, implementation, demonstration, and evaluation. |
| Editable Visual Paradigm project | Assignment06_V01_Multimodal_Search.vpp | Use-case, three-layer class diagram with class dependencies, and voice-search sequence diagrams. |
| Diagram exports | diagrams/ | PNG and SVG files for all three diagrams. |
| Python prototype | main.py, web_demo.py, presentation/, application/, data/ | Text, voice, image, multimodal search, and order lookup. |
| Browser demonstration | web_demo.py, web/ | Local web page with microphone input and real Open Food Facts photos. |
| Teaching data | data/products.json, data/orders.json | Twelve example products and three orders for console text, voice, and order checks. No generated product images. |
| Open-source evaluation data | Google Drive ZIP; extract to data/openfoodfacts/ | 500 real product records, 500 catalog photos, 100 held-out query photos, and attribution notes. |
| Demonstration output | demo/run.txt, demo/console_capture.png, demo/web_capture.png, demo/voice_capture.png | Console output and screenshots of the running prototype. |
| Evaluation results | demo/evaluation.json, demo/openfoodfacts_evaluation.json | Teaching-catalog checks and real-photo results from the submitted app. |
| Tests | tests/test_search.py | Thirteen tests for search modes, filters, the Vision index, and order access. |

## Project directory structure

```text
A6_V01_VuHungAnh/
├── Assignment06_V01_Multimodal_Search.vpp
├── README.md
├── requirements.txt
├── main.py
├── web_demo.py, web/              # Local browser demonstration
├── presentation/                 # User interface
├── application/                  # Query, search, image, speech, and ranking services
├── data/
│   ├── products.json, orders.json
│   ├── vision_backend.swift         # Local Apple Vision image index
│   ├── README.md                    # Which files are demo data and which are real data
│   └── openfoodfacts/              # Download separately from Google Drive
├── diagrams/                     # UML exports (PNG and SVG)
├── report/                       # Final PDF report
├── demo/                         # Run captures and evaluation results
├── tests/                         # Automated tests
└── tools/                         # Data preparation, evaluation, and build scripts
```

## Get the dataset with gdown

The GitHub repository contains the source, report, Visual Paradigm project, small teaching records, and saved demonstration results. The 600 real photos and their metadata are stored separately in the [Google Drive folder](https://drive.google.com/drive/folders/1Ta9vMurnYoJzvNcP23Iflulr-EVWIx58). The prepared ZIP contains `openfoodfacts/` as its top-level directory. Run these commands from the directory where you want to clone the repository on macOS:

```sh
git clone https://github.com/scalliontor/A6_V01_VuHungAnh.git
cd A6_V01_VuHungAnh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install gdown==6.4.1
.venv/bin/python -m gdown --no-cookies 'https://drive.google.com/uc?id=1O4NatWYM2FkYDnp-HCyAK1_N2iTWmvyB' -O OpenFoodFacts_A6_V01.zip
printf '%s  %s\n' 'f408086d7655a110200786f9db34180d5fdac31dcfacfca5a3cb452a49102655' 'OpenFoodFacts_A6_V01.zip' | shasum -a 256 -c -
.venv/bin/python -m zipfile -e OpenFoodFacts_A6_V01.zip data
```

The checksum command must print `OpenFoodFacts_A6_V01.zip: OK`. Extraction creates `data/openfoodfacts/products.json`, `image_queries.json`, `manifest.json`, `DATASET.md`, and `images/` with 600 photos. The ZIP and extracted dataset are intentionally ignored by Git. The download was tested without Google account cookies and matched this checksum.

## Run the prototype

Tested with Python 3.12 on macOS. Pillow is the only runtime Python dependency. Image search also requires Swift and Apple's Vision framework, available through the macOS developer tools. Download the dataset above before running the browser, real-photo evaluation, or all tests.

```sh
.venv/bin/python main.py
.venv/bin/python web_demo.py
.venv/bin/python -m unittest discover -s tests -v
```

Open `http://127.0.0.1:8765` after starting `web_demo.py`. The local page shows text, voice, image, and text + image queries over the 500 real Open Food Facts products. For live voice, choose **Voice**, click **Start microphone**, allow browser access, and speak an English product name. The transcript appears in the input and runs through the same search service. You can edit the transcript or type it when microphone recognition is unavailable. Chrome supports the API used here; recognition availability and whether audio is processed locally or by a browser service depend on the browser. The Python server receives only the transcript. Pick a held-out sample photo or upload a JPEG, PNG, or WebP photo for image search. Stop the server with Ctrl+C. The console `main.py` keeps a short text, simulated-voice transcript, and order example on the 12-product teaching catalog.

Run the saved evaluation scripts from the project root:

    .venv/bin/python tools/evaluate.py
    .venv/bin/python tools/evaluate_openfoodfacts.py

## What the prototype does

The application demonstrates:

1. Text search with category, color, brand, and price filters.
2. Live microphone recognition in the browser, with an editable transcript fallback; both feed the same Python voice-search path.
3. Image search using local Apple Vision feature prints.
4. Text-image score fusion.
5. Product details and order lookup scoped to a customer ID.

The design follows Presentation → Application / Intelligence → Data. The UI calls services; repositories read JSON data. Candidate retrieval and result ranking are separate steps.

Text matches receive a score of 1.0 for a product-name token, 0.55 for a metadata token, and 0 for a miss. For images, VectorIndex starts a local Swift process, extracts a Vision feature print for each gallery photo, and compares the query photo with every product. Vision returns a distance: smaller means closer. The app displays similarity as 1 / (1 + distance), which preserves the same order. Image-only search follows that visual order; text-image search combines it with text and a small popularity/stock score.

## Evaluation

The checks below ask whether the expected item appears first. The small teaching catalog tests text, supplied voice transcripts, and order behavior. The voice evaluation measures search after transcription, not microphone recognition accuracy. Image evaluation uses only real Open Food Facts photos; the generated teaching images and their image-evaluation cases have been removed.

Product records come from the official Open Food Facts [random-modulo-1000 metadata sample](https://static.openfoodfacts.org/exports/products.random-modulo-1000.tar.gz); selected product photos come from the Open Food Facts image store. The preparation script keeps records with a usable product name and front photo, then uses a fixed seed to select 500 gallery products and 100 products with a distinct second photo. The gallery indexes each product's front photo; its second photo is held out as the query. The expected match is the same barcode. The source hash and selection details are in `data/openfoodfacts/manifest.json`.

The real-photo evaluation calls the same SearchUI and Vision index that the browser uses. A result is correct when the matching barcode appears first; top-five results are also counted. Category matching checks whether the first result has the same broad Open Food Facts category tag; missing and `undefined` tags are skipped. The title-search query is the product's own catalog name, so it is easier than a free-form shopping request.

| Check | Result | In plain language |
|---|---:|---|
| Teaching text and voice searches | 16 of 16 expected matches; 3 of 3 expected no-match queries handled correctly | Basic text processing and simulated voice work on the teaching catalog. |
| Order access | 4 of 4 checks passed | The demo returns a customer's order and rejects an order owned by someone else. |
| Find the exact same product from another photo | 22 of 100 first; 26 of 100 in the first five | Different package views remain difficult for the Vision method. |
| Find a product in the same category | 16 of 52 first | Only 52 of the 100 photos had usable broad category labels. |
| Search by the exact product title | 83 of 100 first | This tests title lookup, not a free-form shopping request. |

The real-photo checks use 500 gallery products and 100 separate alternate-view photos. The 48 photos without a usable category label are excluded from category matching. Detailed per-query results and additional metrics are in the JSON files under `demo/`.

## Dataset and attribution

The sample uses the Open Food Facts random-modulo-1000 product export. The gallery and query images are held separately so that an alternate view is never indexed as its own answer. Dataset selection, image preparation, source digest, and attribution are documented in `data/openfoodfacts/DATASET.md` and `manifest.json` after download. The raw export is not included; the selected product data and images are in the separate Google Drive ZIP. All web search modes and `tools/evaluate_openfoodfacts.py` use this real catalog. Each record has a barcode and title; 350 of 500 have a brand and 204 have a usable broad category. The 100 held-out photo queries are labeled by their expected product barcode. The browser displays these labels and the category list.

Product records are covered by ODbL 1.0 and the Database Contents License. Product images are covered by CC BY-SA 3.0. See the official [dataset sample documentation](https://github.com/openfoodfacts/openfoodfacts-ai/blob/develop/data-sets.md) and [license guidance](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/). This coursework is not endorsed by Open Food Facts.

## Rebuild generated files

    .venv/bin/python main.py > demo/run.txt
    .venv/bin/python tools/render_demo.py
    .venv/bin/python tools/evaluate.py
    .venv/bin/python tools/evaluate_openfoodfacts.py
    python3.12 tools/build_vp.py
    tectonic report/assignment06_report.tex --outdir report

Visual Paradigm 18.1 is needed only to rebuild the editable project. Tectonic and the Times New Roman and Arial fonts are needed only to rebuild the PDF.

## Limitations

The teaching catalog and its text labels are small. Live microphone recognition depends on browser support, microphone permission, and the browser's recognition service; the saved voice evaluation uses supplied transcripts. Text normalization uses a short English synonym list. The Open Food Facts sample has no shop prices, stock measurements, or colors; some brands and categories are missing. Apple Vision image search runs locally on macOS and finds the exact product first for only 22% of the alternate-view photos in this sample. Order lookup checks the supplied customer ID but does not provide user authentication.
