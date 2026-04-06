from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from orders.entities.product import Product
from orders.entities.order import Order


class TestMyView(TestCase):
    @patch('orders.my_views.product_service')
    def test_process_order_should_return(self, mock_product_service):
        products = [
            Product(available=15, lead_time=30, type="NORMAL",    name="USB Cable"),
            Product(available=10, lead_time=0,  type="NORMAL",    name="USB Dongle"),
            Product(available=15, lead_time=30, type="EXPIRABLE", name="Butter",
                    expiry_date=date.today() + timedelta(days=26)),
            Product(available=90, lead_time=6,  type="EXPIRABLE", name="Milk",
                    expiry_date=date.today() - timedelta(days=2)),
            Product(available=15, lead_time=30, type="SEASONAL",  name="Watermelon",
                    season_start_date=date.today() - timedelta(days=2),
                    season_end_date=date.today() + timedelta(days=58)),
            Product(available=15, lead_time=30, type="SEASONAL",  name="Grapes",
                    season_start_date=date.today() + timedelta(days=180),
                    season_end_date=date.today() + timedelta(days=240)),
        ]
        for product in products:
            product.save()

        order = Order.objects.create()
        order.products.set(products)

        url = reverse('process_order', args=[order.id])
        response = self.client.post(url, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        result_order = Order.objects.get(id=order.id)
        self.assertEqual(result_order.id, order.id)
