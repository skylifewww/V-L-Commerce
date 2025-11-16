from django.http import JsonResponse
from django.views.decorators.http import require_GET
from eshop.models import Product

@require_GET
def product_api(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        data = {
            'id': product.id,
            'name': product.name,
            'price': str(product.price),
            'old_price': str(product.old_price) if product.old_price else '',
            'description': product.description,
            'sku': product.sku,
            'image_url': product.image.url if product.image else '',
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
