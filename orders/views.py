from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .dto.product import ProcessOrderResponse
from .services.implementations.order_service import OrderNotFound, OrderService


@csrf_exempt
@require_POST
def process_order(request, order_id):
    try:
        order = OrderService().process(order_id)
    except OrderNotFound as e:
        return JsonResponse({'error': str(e)}, status=404)
    except DatabaseError:
        return JsonResponse({'error': f'Order {order_id} could not be processed'}, status=500)
    response = ProcessOrderResponse(order.id)
    return JsonResponse({'id': response.id}, status=200)
