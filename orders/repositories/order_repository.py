from ..entities.order import Order


class OrderRepository:
    def find_by_id(self, order_id):
        return Order.objects.filter(pk=order_id).first()
