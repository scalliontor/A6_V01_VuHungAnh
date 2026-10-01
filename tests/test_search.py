import tempfile
import unittest
from pathlib import Path

from PIL import Image

from main import create_ui
from application.query_service import QueryService
from application.image_service import ImageService
from application.order_service import OrderService
from application.search_service import SearchService
from data.order_repository import OrderRepository
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex
from presentation.search_ui import SearchUI


ROOT = Path(__file__).resolve().parents[1]


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = create_ui()
        repository = ProductRepository(ROOT / "data/openfoodfacts/products.json")
        cls.real_ui = SearchUI(
            SearchService(repository, VectorIndex(repository)),
            ImageService(), OrderService(OrderRepository()),
        )

    @classmethod
    def tearDownClass(cls):
        cls.real_ui.search_service.vector_index.close()

    def test_text_and_voice_modes(self):
        self.assertEqual(self.ui.text("Nike shoes under 100 dollars")[1][0]["product"]["id"], 1)
        self.assertEqual(self.ui.voice("find black running shoes")[1][0]["product"]["id"], 1)

    def test_query_normalization_extracts_constraints_and_synonyms(self):
        query, _ = self.ui.text("Find blue sports shirt under $30")
        self.assertEqual(query["tokens"], ["blue", "sports", "shirt"])
        self.assertEqual(query["category"], "shirt")
        self.assertEqual(query["color"], "blue")
        self.assertEqual(query["max_price"], 30.0)

        query, results = self.ui.text("Nike sneakers")
        self.assertEqual(query["category"], "shoes")
        self.assertEqual(query["brand"], "nike")
        self.assertEqual(results[0]["product"]["id"], 1)

    def test_unicode_accents_normalize_consistently_for_query_and_catalog(self):
        query = QueryService().text_query("Crème brûlée")
        product = {
            "name": "Crème brûlée", "category": "dessert", "brand": "", "color": "",
            "description": "",
        }
        self.assertEqual(query["tokens"], ["creme", "brulee"])
        self.assertEqual(SearchService.text_score(query["tokens"], product), 1.0)

    def test_category_and_color_constraints_resolve_ambiguous_tokens(self):
        query, results = self.ui.text("blue sports shirt")
        self.assertEqual(query["category"], "shirt")
        self.assertEqual(query["color"], "blue")
        self.assertEqual([row["product"]["id"] for row in results], [7])

    def test_sneaker_synonym_returns_relevant_shoe_catalog(self):
        query, results = self.ui.text("sneakers")
        self.assertEqual(query["tokens"], ["shoes"])
        self.assertEqual(query["category"], "shoes")
        self.assertEqual(results[0]["product"]["id"], 1)
        self.assertEqual({row["product"]["id"] for row in results}, {1, 2, 3, 4})

    def test_price_limit_is_strict_and_applied_before_ranking(self):
        _, boundary = self.ui.text("Nike shoes under 95")
        _, below = self.ui.text("Nike shoes under 96")
        self.assertEqual(boundary, [])
        self.assertEqual([row["product"]["id"] for row in below], [1])

    def test_explicit_constraints_can_produce_no_match(self):
        _, results = self.ui.text("red water bottle")
        self.assertEqual(results, [])
        query, results = self.ui.text("purple backpack")
        self.assertEqual(query["color"], "purple")
        self.assertEqual(results, [])

    def test_multimodal_uses_real_photo_and_text(self):
        _, results = self.real_ui.multimodal(
            "Tomato Mushroom Pasta Sauce",
            ROOT / "data/openfoodfacts/images/5010251561958_query.jpg",
        )
        self.assertEqual(results[0]["product"]["id"], "5010251561958")

    def test_vision_index_ranks_real_product_photo(self):
        scores = self.real_ui.search_service.vector_index.scores(
            ROOT / "data/openfoodfacts/images/5010251561958_query.jpg"
        )
        self.assertEqual(len(scores), 500)
        self.assertTrue(all(0 < score <= 1 for score in scores.values()))
        self.assertEqual(max(scores, key=scores.get), "5010251561958")

    def test_missing_real_prices_do_not_crash_filtering(self):
        self.assertEqual(self.real_ui.text("pasta sauce under 5")[1], [])

    def test_blank_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            blank_path = Path(temporary_directory) / "blank.png"
            Image.new("RGB", (64, 64), "white").save(blank_path)
            with self.assertRaisesRegex(ValueError, "no foreground"):
                self.real_ui.image(blank_path)

    def test_empty_text_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Text query is empty"):
            self.ui.text("   ")

    def test_order_access_is_scoped_to_customer(self):
        self.assertIsNone(self.ui.order("C002", "O001"))
        self.assertEqual(self.ui.order("C001", "O001")["status"], "Shipped")
        self.assertEqual(self.ui.order_text("C001", "find my order 20261001")["status"], "Processing")
        self.assertEqual(self.ui.order_text("C001", "where is my latest order?")["order_id"], "20261001")
        self.assertIsNone(self.ui.order_text("C002", "find my order 20261001"))


if __name__ == "__main__":
    unittest.main()
