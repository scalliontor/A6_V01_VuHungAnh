"""Console presentation; orchestration stays outside persistence adapters."""
from application.query_service import QueryService
from application.speech_service import SpeechService


class SearchUI:
    def __init__(self, search_service, image_service, order_service):
        self.search_service = search_service
        self.image_service = image_service
        self.order_service = order_service
        self.query_service = QueryService(search_service.query_metadata())
        self.speech_service = SpeechService()

    def text(self, text):
        query = self.query_service.text_query(text)
        return query, self.search_service.search(query)

    def voice(self, transcript):
        recognized = self.speech_service.transcribe(transcript)
        query = self.query_service.voice_query(recognized)
        return query, self.search_service.search(query)

    def image(self, image_path):
        self.image_service.validate(image_path)
        query = self.query_service.image_query(image_path)
        return query, self.search_service.search(query)

    def multimodal(self, text, image_path):
        self.image_service.validate(image_path)
        query = self.query_service.multimodal_query(text, image_path)
        return query, self.search_service.search(query)

    def order(self, customer_id, order_id=None):
        return self.order_service.search(customer_id, order_id)

    def order_text(self, customer_id, text):
        return self.order_service.search_text(customer_id, text)

    def view_product(self, product_id):
        return self.search_service.view_product(product_id)

    @staticmethod
    def format_results(query, results):
        details = (f"type={query['type']}, input={query['raw']!r}, tokens={query['tokens']}, "
                   f"category={query.get('category')}, color={query.get('color')}, "
                   f"brand={query.get('brand')}, max_price={query['max_price']}")
        rows = [details, "Retrieval -> ranking -> top results:"]
        rows += [f"  {index}. {item['product']['name']} | score={item['score']:.4f} "
                 f"(text={item['text_score']:.3f}, image={item['image_score']:.3f}, business={item['business_score']:.3f})"
                 for index, item in enumerate(results, 1)]
        return "\n".join(rows if results else rows + ["  No matching products"])
