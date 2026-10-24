from django.db import transaction
from django.utils import timezone

from ...repositories.order_repository import OrderRepository
from ...repositories.product_repository import ProductRepository
from .product_service import ProductService


class OrderNotFound(Exception):
    def __init__(self, order_id):
        super().__init__(f"Order {order_id} not found")
        self.order_id = order_id


class OrderService:
    def __init__(self, order_repository=None, product_repository=None, product_service=None):
        self.order_repository = order_repository or OrderRepository()
        self.product_repository = product_repository or ProductRepository()
        self.product_service = product_service or ProductService(self.product_repository)

    def process(self, order_id, today=None):
        today = today or timezone.localdate()
        with transaction.atomic():
            order = self.order_repository.find_by_id(order_id)
            if order is None:
                raise OrderNotFound(order_id)
            for product in self.product_repository.find_by_order_for_update(order):
                self.product_service.process(product, today)
        return order
