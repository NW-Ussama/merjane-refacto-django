from ..entities.product import Product

class ProductRepository:
    # Constat des mêmes problèmes que pour OrderRepository, find_by_id doit retourner un objet ou None
    # Id est un built_in python, pas de nommage id pour les variables
    def find_by_id(self, product_id):
        try:
            return Product.objects.filter(pk=product_id)
        except Product.DoesNotExist:
            return None

    def save(self, product):
        product.save()

# respect du snake_case pour les variables
product_repository = ProductRepository()
