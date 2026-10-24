import unittest
from datetime import date, timedelta
from unittest.mock import Mock

from orders.entities.product import Product, ProductType
from orders.services.implementations.product_service import ProductService

TODAY = date(2026, 6, 15)


def days(n):
    return TODAY + timedelta(days=n)


class ProductServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = Mock()
        self.notifier = Mock()
        self.service = ProductService(self.repo, self.notifier)

    def assert_no_notification(self):
        self.notifier.send_delay_notification.assert_not_called()
        self.notifier.send_out_of_stock_notification.assert_not_called()
        self.notifier.send_expiry_notification.assert_not_called()


class NormalProductTests(ProductServiceTestCase):
    def product(self, **kwargs):
        return Product(name="RJ45 Cable", type=ProductType.NORMAL, **kwargs)

    def test_in_stock_is_consumed(self):
        p = self.product(available=3, lead_time=15)

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 2)
        self.repo.save_available.assert_called_once_with(p)
        self.assert_no_notification()

    def test_out_of_stock_with_lead_time_notifies_delay(self):
        p = self.product(available=0, lead_time=15)

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 0)
        self.repo.save_available.assert_not_called()
        self.notifier.send_delay_notification.assert_called_once_with(15, "RJ45 Cable")

    def test_out_of_stock_without_lead_time_does_nothing(self):
        p = self.product(available=0, lead_time=0)

        self.service.process(p, TODAY)

        self.repo.save_available.assert_not_called()
        self.assert_no_notification()


class SeasonalProductTests(ProductServiceTestCase):
    def product(self, **kwargs):
        return Product(name="Watermelon", type=ProductType.SEASONAL, **kwargs)

    def test_in_season_and_in_stock_is_consumed(self):
        p = self.product(available=5, lead_time=10, season_start_date=days(-5), season_end_date=days(30))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 4)
        self.assert_no_notification()

    def test_season_boundaries_are_inclusive(self):
        for start, end in [(days(0), days(30)), (days(-30), days(0))]:
            with self.subTest(start=start, end=end):
                p = self.product(available=5, lead_time=0, season_start_date=start, season_end_date=end)

                self.service.process(p, TODAY)

                self.assertEqual(p.available, 4)

    def test_restock_after_season_end_marks_out_of_stock(self):
        p = self.product(available=0, lead_time=20, season_start_date=days(-5), season_end_date=days(10))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 0)
        self.repo.save_available.assert_not_called()
        self.notifier.send_out_of_stock_notification.assert_called_once_with("Watermelon")

    def test_after_season_end_clears_remaining_stock(self):
        p = self.product(available=5, lead_time=0, season_start_date=days(-30), season_end_date=days(-1))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 0)
        self.repo.save_available.assert_called_once_with(p)
        self.notifier.send_out_of_stock_notification.assert_called_once_with("Watermelon")

    def test_before_season_with_long_lead_time_keeps_stock(self):
        p = self.product(available=50, lead_time=90, season_start_date=days(30), season_end_date=days(60))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 50)
        self.repo.save_available.assert_not_called()
        self.notifier.send_out_of_stock_notification.assert_called_once_with("Watermelon")

    def test_in_season_out_of_stock_without_lead_time_does_nothing(self):
        p = self.product(available=0, lead_time=0, season_start_date=days(-5), season_end_date=days(30))

        self.service.process(p, TODAY)

        self.repo.save_available.assert_not_called()
        self.assert_no_notification()

    def test_before_season_notifies_out_of_stock_without_changing_stock(self):
        p = self.product(available=5, lead_time=10, season_start_date=days(30), season_end_date=days(90))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 5)
        self.repo.save_available.assert_not_called()
        self.notifier.send_out_of_stock_notification.assert_called_once_with("Watermelon")

    def test_in_season_out_of_stock_with_restock_in_time_notifies_delay(self):
        p = self.product(available=0, lead_time=5, season_start_date=days(-5), season_end_date=days(30))

        self.service.process(p, TODAY)

        self.notifier.send_delay_notification.assert_called_once_with(5, "Watermelon")
        self.notifier.send_out_of_stock_notification.assert_not_called()

    def test_missing_season_dates_is_out_of_stock(self):
        p = self.product(available=5, lead_time=5)

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 5)
        self.notifier.send_out_of_stock_notification.assert_called_once_with("Watermelon")


class ExpirableProductTests(ProductServiceTestCase):
    def product(self, **kwargs):
        return Product(name="Butter", type=ProductType.EXPIRABLE, **kwargs)

    def test_fresh_and_in_stock_is_consumed(self):
        p = self.product(available=5, expiry_date=days(10))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 4)
        self.assert_no_notification()

    def test_expiring_today_is_still_sold(self):
        p = self.product(available=5, expiry_date=days(0))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 4)
        self.assert_no_notification()

    def test_not_expired_out_of_stock_notifies_delay(self):
        p = self.product(available=0, lead_time=7, expiry_date=days(10))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 0)
        self.repo.save_available.assert_not_called()
        self.notifier.send_delay_notification.assert_called_once_with(7, "Butter")
        self.notifier.send_expiry_notification.assert_not_called()

    def test_expired_clears_stock_and_notifies(self):
        p = self.product(available=5, expiry_date=days(-1))

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 0)
        self.repo.save_available.assert_called_once_with(p)
        self.notifier.send_expiry_notification.assert_called_once_with("Butter")

    def test_expired_without_stock_is_not_saved_again(self):
        p = self.product(available=0, expiry_date=days(-1))

        self.service.process(p, TODAY)

        self.repo.save_available.assert_not_called()
        self.notifier.send_expiry_notification.assert_called_once_with("Butter")

    def test_missing_expiry_date_is_treated_as_expired(self):
        p = self.product(available=5)

        self.service.process(p, TODAY)

        self.assertEqual(p.available, 0)
        self.notifier.send_expiry_notification.assert_called_once_with("Butter")


class UnknownProductTypeTests(ProductServiceTestCase):
    def test_unknown_type_is_skipped(self):
        p = Product(name="Mystery", type="UNKNOWN", available=5)

        with self.assertLogs('orders.services.implementations.product_service', level='WARNING'):
            self.service.process(p, TODAY)

        self.assertEqual(p.available, 5)
        self.repo.save_available.assert_not_called()
        self.assert_no_notification()


if __name__ == '__main__':
    unittest.main()
