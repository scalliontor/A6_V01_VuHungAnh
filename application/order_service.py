"""Application boundary for customer-scoped order lookup."""
import re


class OrderService:
    def __init__(self, repository):
        self.repository = repository

    def search(self, customer_id, order_id=None):
        return (self.repository.find_order(order_id, customer_id) if order_id
                else self.repository.latest_order(customer_id))

    def search_text(self, customer_id, text):
        """Handle the two order requests in the assignment's problem statement."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Order query is empty")
        if re.search(r"\b(latest|newest|most recent)\b", text, re.IGNORECASE):
            return self.search(customer_id)
        match = re.search(r"\border\s*(?:number\s*|id\s*|#\s*)?([a-z]?\d+)\b", text, re.IGNORECASE)
        return self.search(customer_id, match.group(1)) if match else None
