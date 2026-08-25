"""Per-type product handlers.

Each product type (NORMAL, SEASONAL, EXPIRABLE) has its own set of rules for
what happens when it is part of a processed order. Instead of a big
``if p.type == ...`` chain spread across the view and the service, every type
gets a small handler that owns its *complete* logic (both the in-stock happy
path and the out-of-stock / unavailable edge cases).

Handlers receive their collaborators (the product repository and the
notification service) by injection, which keeps them easy to unit-test.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta


class ProductHandler(ABC):
    def __init__(self, product_repository, notification_service):
        self.products = product_repository
        self.notifications = notification_service

    @abstractmethod
    def handle(self, product):
        """Apply this type's rules to ``product`` for the current order."""

    def _sell_one(self, product):
        product.available -= 1
        self.products.save(product)

    def _notify_delay(self, product):
        self.products.save(product)
        self.notifications.send_delay_notification(product.lead_time, product.name)


class NormalProductHandler(ProductHandler):
    def handle(self, product):
        if product.available > 0:
            self._sell_one(product)
        elif product.lead_time > 0:
            self._notify_delay(product)


class SeasonalProductHandler(ProductHandler):
    def handle(self, product):
        today = date.today()
        if product.available > 0 and self._in_season(product, today):
            self._sell_one(product)
        elif self._restock_after_season_end(product, today):
            self._notify_unavailable(product)
        elif product.season_start_date > today:
            self.notifications.send_out_of_stock_notification(product.name)
            self.products.save(product)
        else:
            self._notify_delay(product)

    def _in_season(self, product, today):
        return product.season_start_date < today < product.season_end_date

    def _restock_after_season_end(self, product, today):
        return today + timedelta(days=product.lead_time) > product.season_end_date

    def _notify_unavailable(self, product):
        self.notifications.send_out_of_stock_notification(product.name)
        product.available = 0
        self.products.save(product)


class ExpirableProductHandler(ProductHandler):
    def handle(self, product):
        today = date.today()
        if product.available > 0 and product.expiry_date > today:
            self._sell_one(product)
        else:
            product.available = 0
            self.products.save(product)
            self.notifications.send_expiry_notification(product.name)
