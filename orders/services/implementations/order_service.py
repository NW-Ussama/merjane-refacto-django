"""Order service: orchestrates processing of every product in an order.

It loads the order, hands each product to the product service, and returns the
processed order. Keeping this loop out of the view leaves the controller thin.
"""

from ...repositories.order_repository import or_
from .product_service import ps


class OrderService:
    def __init__(self, order_repository=or_, product_service=ps):
        self.orders = order_repository
        self.products = product_service

    def process_order(self, order_id):
        order = self.orders.find_by_id(order_id).get()
        for product in order.get_items():
            self.products.process(product)
        return order


order_service = OrderService()
