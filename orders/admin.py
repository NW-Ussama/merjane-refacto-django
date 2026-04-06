from django.contrib import admin
from .entities.product import Product
from .entities.order import Order

# Register your models here.
admin.site.register(Product)
admin.site.register(Order)
