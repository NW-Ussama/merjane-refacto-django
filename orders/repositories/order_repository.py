from ..entities.order import Order

class OrderRepository:
    def find_by_id(self, order_id):
        # la fonction deoit retourner un objet ou un None
        # id est yun built_in python => pas de nommage id pour les variables
        try:
            return Order.objects.filter(pk=order_id)
        except Order.DoesNotExist:
            return None

    def save(self, order):
        order.save()

# respect du snake_case pour les variables       
order_repository = OrderRepository()
