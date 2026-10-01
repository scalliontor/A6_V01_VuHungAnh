import json
from pathlib import Path


class OrderRepository:
    def __init__(self, path=None):
        source = Path(path) if path else Path(__file__).with_name("orders.json")
        self.orders = json.loads(source.read_text(encoding="utf-8"))

    def find_order(self, order_id, customer_id):
        return next((order for order in self.orders if order["order_id"].lower() == order_id.lower()
                     and order["customer_id"] == customer_id), None)

    def latest_order(self, customer_id):
        owned = [order for order in self.orders if order["customer_id"] == customer_id]
        return max(owned, key=lambda order: order["date"], default=None)
