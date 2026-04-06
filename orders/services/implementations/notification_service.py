# WARN: Should not be changed during the exercise
class NotificationService:
    def send_delay_notification(self, lead_time, product_name):
        """
        Notify that a product is delayed by the given lead time.
        """
        pass

    def send_out_of_stock_notification(self, product_name):
        """
        Notify that a seasonal product is out of season.
        """
        pass

    def send_expiry_notification(self, product_name):
        """
        Notify that a product has expired or is expiring.
        """
        pass

notification_service = NotificationService()
