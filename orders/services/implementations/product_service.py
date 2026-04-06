from datetime import date, timedelta
from ...repositories.product_repository import product_repository
from .notification_service import notification_service

class ProductService:
    """ 
        Classe de service pour gérer la logique métier liée aux produits, notamment les notifications en cas de retard.
    """
    def __init__(self, product_repository, notification_service):
        """
        Initialise le service de produits.
        """
        self.product_repository = product_repository
        self.notification_service = notification_service

    def notify_delay(self, product):
        """
        Notifie un retard pour un produit.
        """
        self.product_repository.save(product)
        self.notification_service.send_delay_notification(product.lead_time, product.name)

    def handle_seasonal_product(self, product):
        """
        Gère un produit saisonnier.
        """
        if date.today() + timedelta(days=product.lead_time) > product.season_end_date:
            notification_service.send_out_of_stock_notification(product.name)
            product.available = 0
            product_repository.save(product)
        elif product.season_start_date > date.today():
            notification_service.send_out_of_stock_notification(product.name)
            product_repository.save(product)
        else:
            self.notify_delay(product)

    def handle_expired_product(self, product):
        """
        Gère un produit expiré.
        """
        product.available = 0
        self.product_repository.save(product)
        self.notification_service.send_expiry_notification(product.name)

    def process_order(self, order):
        """
        Traite une commande en fonction du type de produit.
        """
        today_ = date.today()
        for product in order.get_items():
            if product.type == "NORMAL":
                self._process_normal(product)
            elif product.type == "SEASONAL":
                self._process_seasonal(product, today_)
            elif product.type == "EXPIRABLE":
                self._process_expirable(product, today_)

    def _process_normal(self, product):
        """
        Traite un produit normal."""
        if product.available > 0:
            product.available -= 1
            self.product_repository.save(product)
        elif product.lead_time > 0:
            self.notify_delay(product)

    def _process_seasonal(self, product, today):
        """
        Traite un produit saisonnier.
        """
        if product.season_start_date <= today <= product.season_end_date and product.available > 0:
            product.available -= 1
            self.product_repository.save(product)
        else:
            self.handle_seasonal_product(product)

    def _process_expirable(self, product, today):
        """"
        Traite un produit expiré.
        """
        if product.available > 0 and product.expiry_date > today:
            product.available -= 1
            self.product_repository.save(product)
        else:
            self.handle_expired_product(product)

product_service = ProductService(product_repository, notification_service)
