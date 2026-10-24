import logging
from datetime import timedelta
from functools import partial

from django.db import transaction

from ...entities.product import ProductType
from ...repositories.product_repository import ProductRepository
from .notification_service import ns

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, product_repository=None, notification_service=None):
        self.product_repository = product_repository or ProductRepository()
        self.notification_service = notification_service or ns
        self._handlers = {
            ProductType.NORMAL: self.handle_normal_product,
            ProductType.SEASONAL: self.handle_seasonal_product,
            ProductType.EXPIRABLE: self.handle_expirable_product,
        }

    def process(self, product, today):
        handler = self._handlers.get(product.type)
        if handler is None:
            logger.warning("Skipping product %s with unknown type %r", product.pk, product.type)
            return
        handler(product, today)

    def handle_normal_product(self, product, today):
        if product.available > 0:
            self._consume(product)
        elif product.lead_time > 0:
            self.notify_delay(product)

    def handle_seasonal_product(self, product, today):
        start, end = product.season_start_date, product.season_end_date
        if start is None or end is None:
            self._notify(self.notification_service.send_out_of_stock_notification, product.name)
            return

        if start > today:
            self._notify(self.notification_service.send_out_of_stock_notification, product.name)
        elif today <= end and product.available > 0:
            self._consume(product)
        elif today + timedelta(days=product.lead_time) > end:
            self._clear_stock(product)
            self._notify(self.notification_service.send_out_of_stock_notification, product.name)
        elif product.lead_time > 0:
            self.notify_delay(product)

    def handle_expirable_product(self, product, today):
        expiry = product.expiry_date
        if expiry is None or expiry < today:
            self.handle_expired_product(product)
        else:
            self.handle_normal_product(product, today)

    def handle_expired_product(self, product):
        self._clear_stock(product)
        self._notify(self.notification_service.send_expiry_notification, product.name)

    def notify_delay(self, product):
        self._notify(self.notification_service.send_delay_notification, product.lead_time, product.name)

    def _notify(self, send, *args):
        # Only notify once the stock changes are committed
        transaction.on_commit(partial(send, *args))

    def _consume(self, product):
        product.available -= 1
        self.product_repository.save_available(product)

    def _clear_stock(self, product):
        if product.available != 0:
            product.available = 0
            self.product_repository.save_available(product)
