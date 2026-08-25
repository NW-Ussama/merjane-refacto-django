"""Product service: routes a product to the handler for its type.

This is a thin dispatcher. It holds no per-type logic itself — it only maps a
product ``type`` to the handler that knows the rules. Adding a new product type
means adding a handler and one entry in the registry below.
"""

from ...entities.product import Product
from ...repositories.product_repository import pr
from ..handlers import (
    ExpirableProductHandler,
    NormalProductHandler,
    SeasonalProductHandler,
)
from .notification_service import ns


class ProductService:
    def __init__(self, product_repository=pr, notification_service=ns):
        self._handlers = {
            Product.NORMAL: NormalProductHandler(product_repository, notification_service),
            Product.SEASONAL: SeasonalProductHandler(product_repository, notification_service),
            Product.EXPIRABLE: ExpirableProductHandler(product_repository, notification_service),
        }

    def process(self, product):
        handler = self._handlers.get(product.type)
        if handler is not None:
            handler.handle(product)


ps = ProductService()
