# orders/tests/test_product_service_unit.py

import unittest
from unittest.mock import patch

from orders.entities.product import Product
from orders.services.implementations.product_service import ProductService

class MyUnitTests(unittest.TestCase):
    @patch('orders.services.implementations.product_service.notification_service')
    @patch('orders.services.implementations.product_service.product_repository')
    def test_notify_delay(self, mock_product_repository, mock_notification_service):
        product = Product(
            name="RJ45 Cable",
            type="NORMAL",
            available=0,
            lead_time=15,
        )
        mock_product_repository.save.return_value = product
        product_service = ProductService(mock_product_repository, mock_notification_service)

        product_service.notify_delay(product)

        self.assertEqual(0, product.available)
        self.assertEqual(15, product.lead_time)
        mock_product_repository.save.assert_called_once_with(product)
        mock_notification_service.send_delay_notification.assert_called_once_with(product.lead_time, product.name)

if __name__ == '__main__':
    unittest.main()
