import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .repositories.order_repository import order_repository
from .services.implementations.product_service import product_service

logger = logging.getLogger(__name__)

# crsf_exempt est utilisé pour permettre les requêtes POST mais dangereyx en prod
@csrf_exempt
@require_POST
def process_order(request, order_id):
    order = order_repository.find_by_id(order_id).get()
    if order is None:
        return JsonResponse({'error': 'Order not found'}, status=404)
    
    # Suppression du print, erreur fatale en prod !!
    ## Remplacement par Logging
    logger.debug("Processing order: %s", order_id)

    product_service.process_order(order)    

    return JsonResponse({'id': order.id}, status=200)
