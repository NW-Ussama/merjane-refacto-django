"""View / integration tests for the order-processing endpoint.

These exercise ``POST /orders/<id>/processOrder`` end to end, one test per
business branch, asserting the final stock and the notification produced. They
were written before refactoring to describe current behavior and act as a
regression net: as long as they stay green, no behavior changed.

Notifications are produced by the ``NotificationService`` singleton (``ns``)
used inside the product service, so we patch it there and assert on the calls.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from orders.entities.order import Order
from orders.entities.product import Product
from orders.services.implementations.order_service import OrderService
from orders.services.implementations.product_service import ProductService

TODAY = date.today()


def days(n):
    return TODAY + timedelta(days=n)


class ProcessOrderViewTest(TestCase):
    def setUp(self):
        # NotificationService is the external boundary, so we mock it and inject
        # it through the real service graph used by the view. This lets us
        # assert on the notifications produced while exercising the real rules.
        self.ns = MagicMock()
        service = OrderService(
            product_service=ProductService(notification_service=self.ns))
        patcher = patch('orders.my_views.order_service', service)
        patcher.start()
        self.addCleanup(patcher.stop)

    def process_single(self, **product_kwargs):
        """Create an order with a single product, process it, then return the
        reloaded product and the HTTP response."""
        product = Product.objects.create(**product_kwargs)
        order = Order.objects.create()
        order.products.set([product])

        response = self.client.post(
            reverse('process_order', args=[order.id]),
            content_type="application/json",
        )
        product.refresh_from_db()
        return product, response

    # ----- NORMAL -----------------------------------------------------------

    def test_normal_in_stock_is_sold(self):
        product, response = self.process_single(
            name="USB Cable", type="NORMAL", available=15, lead_time=30)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(product.available, 14)
        self.ns.send_delay_notification.assert_not_called()

    def test_normal_out_of_stock_with_lead_time_notifies_delay(self):
        product, _ = self.process_single(
            name="USB Dongle", type="NORMAL", available=0, lead_time=15)

        self.assertEqual(product.available, 0)
        self.ns.send_delay_notification.assert_called_once_with(15, "USB Dongle")

    def test_normal_out_of_stock_without_lead_time_does_nothing(self):
        product, _ = self.process_single(
            name="USB Dongle", type="NORMAL", available=0, lead_time=0)

        self.assertEqual(product.available, 0)
        self.ns.send_delay_notification.assert_not_called()

    # ----- SEASONAL ---------------------------------------------------------

    def test_seasonal_in_season_in_stock_is_sold(self):
        product, _ = self.process_single(
            name="Watermelon", type="SEASONAL", available=15, lead_time=30,
            season_start_date=days(-2), season_end_date=days(58))

        self.assertEqual(product.available, 14)
        self.ns.send_delay_notification.assert_not_called()
        self.ns.send_out_of_stock_notification.assert_not_called()

    def test_seasonal_in_season_out_of_stock_restock_fits_notifies_delay(self):
        product, _ = self.process_single(
            name="Watermelon", type="SEASONAL", available=0, lead_time=5,
            season_start_date=days(-10), season_end_date=days(60))

        self.assertEqual(product.available, 0)
        self.ns.send_delay_notification.assert_called_once_with(5, "Watermelon")

    def test_seasonal_restock_after_season_end_is_unavailable(self):
        product, _ = self.process_single(
            name="Watermelon", type="SEASONAL", available=0, lead_time=30,
            season_start_date=days(-10), season_end_date=days(3))

        self.assertEqual(product.available, 0)
        self.ns.send_out_of_stock_notification.assert_called_once_with("Watermelon")

    def test_seasonal_before_season_start_is_out_of_stock(self):
        product, _ = self.process_single(
            name="Grapes", type="SEASONAL", available=15, lead_time=30,
            season_start_date=days(180), season_end_date=days(240))

        self.assertEqual(product.available, 15)
        self.ns.send_out_of_stock_notification.assert_called_once_with("Grapes")

    # ----- EXPIRABLE --------------------------------------------------------

    def test_expirable_in_stock_not_expired_is_sold(self):
        product, _ = self.process_single(
            name="Butter", type="EXPIRABLE", available=15, lead_time=30,
            expiry_date=days(26))

        self.assertEqual(product.available, 14)
        self.ns.send_expiry_notification.assert_not_called()

    def test_expirable_expired_is_unavailable_and_notifies(self):
        product, _ = self.process_single(
            name="Milk", type="EXPIRABLE", available=90, lead_time=6,
            expiry_date=days(-2))

        self.assertEqual(product.available, 0)
        self.ns.send_expiry_notification.assert_called_once_with("Milk")

    def test_expirable_out_of_stock_notifies_expiry(self):
        product, _ = self.process_single(
            name="Milk", type="EXPIRABLE", available=0, lead_time=6,
            expiry_date=days(26))

        self.assertEqual(product.available, 0)
        self.ns.send_expiry_notification.assert_called_once_with("Milk")
