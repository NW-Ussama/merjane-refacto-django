from django.db import models


class ProductType(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    SEASONAL = 'SEASONAL', 'Seasonal'
    EXPIRABLE = 'EXPIRABLE', 'Expirable'


class Product(models.Model):
    name              = models.CharField(max_length=100)
    type              = models.CharField(max_length=20, choices=ProductType.choices)
    available         = models.IntegerField(default=0)
    lead_time         = models.IntegerField(default=0)
    expiry_date       = models.DateField(null=True, blank=True)
    season_start_date = models.DateField(null=True, blank=True)
    season_end_date   = models.DateField(null=True, blank=True)

    class Meta:
        app_label = 'orders'
