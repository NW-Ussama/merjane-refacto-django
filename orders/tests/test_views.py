from datetime import date, timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from orders.entities.order import Order
from orders.entities.product import Product, ProductType
from orders.repositories.product_repository import ProductRepository
from orders.services.implementations.order_service import OrderService


class TestProcessOrderView(TestCase):
    @patch('orders.services.implementations.product_service.ns')
    def test_process_order_updates_stock_and_notifies(self, mock_ns):
        today = date.today()
        products = {
            'USB Cable': Product(available=15, lead_time=30, type=ProductType.NORMAL, name="USB Cable"),
            'USB Dongle': Product(available=10, lead_time=0, type=ProductType.NORMAL, name="USB Dongle"),
            'Butter': Product(available=15, lead_time=30, type=ProductType.EXPIRABLE, name="Butter",
                              expiry_date=today + timedelta(days=26)),
            'Milk': Product(available=90, lead_time=6, type=ProductType.EXPIRABLE, name="Milk",
                            expiry_date=today - timedelta(days=2)),
            'Watermelon': Product(available=15, lead_time=30, type=ProductType.SEASONAL, name="Watermelon",
                                  season_start_date=today - timedelta(days=2),
                                  season_end_date=today + timedelta(days=58)),
            'Grapes': Product(available=15, lead_time=30, type=ProductType.SEASONAL, name="Grapes",
                              season_start_date=today + timedelta(days=180),
                              season_end_date=today + timedelta(days=240)),
        }
        for p in products.values():
            p.save()
        order = Order.objects.create()
        order.products.set(products.values())

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('process_order', args=[order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'id': order.id})

        available = {p.name: p.available for p in Product.objects.all()}
        self.assertEqual(available, {
            'USB Cable': 14,
            'USB Dongle': 9,
            'Butter': 14,
            'Milk': 0,
            'Watermelon': 14,
            'Grapes': 15,
        })
        mock_ns.send_expiry_notification.assert_called_once_with("Milk")
        mock_ns.send_out_of_stock_notification.assert_called_once_with("Grapes")
        mock_ns.send_delay_notification.assert_not_called()

    @patch('orders.services.implementations.product_service.ns')
    def test_failed_order_rolls_back_stock_and_sends_no_notifications(self, mock_ns):
        milk = Product.objects.create(available=5, lead_time=0, type=ProductType.EXPIRABLE, name="Milk",
                                      expiry_date=date.today() - timedelta(days=1))
        cable = Product.objects.create(available=5, lead_time=0, type=ProductType.NORMAL, name="Cable")
        order = Order.objects.create()
        order.products.set([milk, cable])

        save_available = ProductRepository.save_available
        def fail_on_cable(repo, product):
            if product.name == "Cable":
                raise DatabaseError("boom")
            save_available(repo, product)

        with patch.object(ProductRepository, 'save_available', fail_on_cable), \
                self.captureOnCommitCallbacks(execute=True), \
                self.assertRaises(DatabaseError):
            OrderService().process(order.id)

        milk.refresh_from_db()
        self.assertEqual(milk.available, 5)
        mock_ns.send_expiry_notification.assert_not_called()

    def test_unknown_order_returns_404(self):
        response = self.client.post(reverse('process_order', args=[999]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Order 999 not found'})

    def test_get_is_not_allowed(self):
        order = Order.objects.create()

        response = self.client.get(reverse('process_order', args=[order.id]))

        self.assertEqual(response.status_code, 405)
