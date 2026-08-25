"""Unit tests for the per-type product handlers.

Each handler owns the rules for one product type. Here we test them in
isolation with a mocked repository and notification service (no database), so
every branch is documented and fast to run.
"""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from orders.entities.product import Product
from orders.services.handlers import (
    ExpirableProductHandler,
    NormalProductHandler,
    SeasonalProductHandler,
)

TODAY = date.today()


def days(n):
    return TODAY + timedelta(days=n)


class NormalProductHandlerTest(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.ns = MagicMock()
        self.handler = NormalProductHandler(self.repo, self.ns)

    def test_in_stock_sells_one_unit(self):
        product = Product(name="USB Cable", type="NORMAL", available=5, lead_time=3)

        self.handler.handle(product)

        self.assertEqual(product.available, 4)
        self.repo.save.assert_called_once_with(product)
        self.ns.send_delay_notification.assert_not_called()

    def test_out_of_stock_with_lead_time_notifies_delay(self):
        product = Product(name="USB Cable", type="NORMAL", available=0, lead_time=3)

        self.handler.handle(product)

        self.assertEqual(product.available, 0)
        self.ns.send_delay_notification.assert_called_once_with(3, "USB Cable")

    def test_out_of_stock_without_lead_time_does_nothing(self):
        product = Product(name="USB Cable", type="NORMAL", available=0, lead_time=0)

        self.handler.handle(product)

        self.repo.save.assert_not_called()
        self.ns.send_delay_notification.assert_not_called()


class SeasonalProductHandlerTest(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.ns = MagicMock()
        self.handler = SeasonalProductHandler(self.repo, self.ns)

    def test_in_season_and_in_stock_sells_one_unit(self):
        product = Product(name="Watermelon", type="SEASONAL", available=5, lead_time=3,
                          season_start_date=days(-5), season_end_date=days(30))

        self.handler.handle(product)

        self.assertEqual(product.available, 4)
        self.ns.send_delay_notification.assert_not_called()
        self.ns.send_out_of_stock_notification.assert_not_called()

    def test_in_season_out_of_stock_restock_fits_notifies_delay(self):
        product = Product(name="Watermelon", type="SEASONAL", available=0, lead_time=5,
                          season_start_date=days(-5), season_end_date=days(30))

        self.handler.handle(product)

        self.ns.send_delay_notification.assert_called_once_with(5, "Watermelon")

    def test_restock_after_season_end_marks_unavailable(self):
        product = Product(name="Watermelon", type="SEASONAL", available=0, lead_time=30,
                          season_start_date=days(-5), season_end_date=days(3))

        self.handler.handle(product)

        self.assertEqual(product.available, 0)
        self.ns.send_out_of_stock_notification.assert_called_once_with("Watermelon")

    def test_before_season_start_is_out_of_stock(self):
        product = Product(name="Grapes", type="SEASONAL", available=5, lead_time=1,
                          season_start_date=days(30), season_end_date=days(60))

        self.handler.handle(product)

        self.assertEqual(product.available, 5)
        self.ns.send_out_of_stock_notification.assert_called_once_with("Grapes")


class ExpirableProductHandlerTest(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.ns = MagicMock()
        self.handler = ExpirableProductHandler(self.repo, self.ns)

    def test_in_stock_and_not_expired_sells_one_unit(self):
        product = Product(name="Butter", type="EXPIRABLE", available=5, expiry_date=days(10))

        self.handler.handle(product)

        self.assertEqual(product.available, 4)
        self.ns.send_expiry_notification.assert_not_called()

    def test_expired_marks_unavailable_and_notifies(self):
        product = Product(name="Milk", type="EXPIRABLE", available=5, expiry_date=days(-1))

        self.handler.handle(product)

        self.assertEqual(product.available, 0)
        self.ns.send_expiry_notification.assert_called_once_with("Milk")

    def test_out_of_stock_notifies_expiry(self):
        product = Product(name="Milk", type="EXPIRABLE", available=0, expiry_date=days(10))

        self.handler.handle(product)

        self.assertEqual(product.available, 0)
        self.ns.send_expiry_notification.assert_called_once_with("Milk")


if __name__ == '__main__':
    unittest.main()
