"""Executable demonstration of text, simulated voice, image and fusion search."""
from application.image_service import ImageService
from application.search_service import SearchService
from application.order_service import OrderService
from data.product_repository import ProductRepository
from data.order_repository import OrderRepository
from data.vector_index import VectorIndex
from presentation.search_ui import SearchUI


def create_ui():
    products = ProductRepository()
    images = ImageService()
    index = VectorIndex(products)
    return SearchUI(SearchService(products, index), images, OrderService(OrderRepository()))


def main():
    ui = create_ui()
    samples = [
        ("TEXT: Nike shoes under 100 dollars", ui.text("find Nike shoes under 100 dollars")),
        ("VOICE: black running shoes (transcript simulation)", ui.voice("find black running shoes")),
    ]
    print("=== E-Commerce Multimodal Search Demo ===")
    for title, (query, results) in samples:
        print("\n" + title)
        print(ui.format_results(query, results))
    print("\nORDER: customer C001, 'find my order 20261001'")
    print(ui.order_text("C001", "find my order 20261001"))
    print("\nLATEST ORDER: customer C001, 'where is my latest order?'")
    print(ui.order_text("C001", "where is my latest order?"))
    print("\nFor image and combined search with real Open Food Facts photos, run: python web_demo.py")


if __name__ == "__main__":
    main()
