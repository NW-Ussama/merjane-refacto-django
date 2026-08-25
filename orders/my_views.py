from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .dto.product import ProcessOrderResponse
from .services.implementations.order_service import order_service


@csrf_exempt
@require_POST
def process_order(request, order_id):
    order = order_service.process_order(order_id)
    response = ProcessOrderResponse(order.id)
    return JsonResponse({'id': response.id}, status=200)
