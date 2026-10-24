class ProductRepository:
    def find_by_order_for_update(self, order):
        # Lock rows in a stable order so concurrent orders can't deadlock
        # or decrement the same stock twice.
        return order.get_items().select_for_update().order_by('pk')

    def save_available(self, product):
        product.save(update_fields=['available'])
