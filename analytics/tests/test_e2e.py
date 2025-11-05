import json
from django.test import TestCase, Client
from django.urls import reverse
from eshop.models import Product, Order
from analytics.models import Conversion


class E2EUTMToConversionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(name="Tee", sku="SKU1", price="19.99", stock=10)

    def test_visit_with_utm_then_create_order_records_conversion(self):
        # 1) land with utm -> middleware captures session+campaign
        r = self.client.get(
            "/eshop/products/",
            {"utm_source": "tiktok", "utm_medium": "paid", "utm_campaign": "spring"},
        )
        self.assertEqual(r.status_code, 200)
        # 2) create order via JSON
        payload = {
            "customer_data": {
                "full_name": "John Doe",
                "phone": "+1000000000",
                "email": "john@example.com",
                "address": "Somewhere",
            },
            "products": [
                {"product_id": self.product.id, "quantity": 2}
            ],
            "shipping_address": "Ship addr",
        }
        r2 = self.client.post(
            "/eshop/order/create/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        # Should redirect to order detail
        self.assertEqual(r2.status_code, 302)
        # 3) assert order stored with analytics fields and conversion created
        order = Order.objects.order_by("-id").first()
        self.assertIsNotNone(order)
        self.assertTrue(order.tiktok_source)
        self.assertIsNotNone(order.conversion_value)
        conv = Conversion.objects.filter(order=order).first()
        self.assertIsNotNone(conv)
        self.assertEqual(conv.conversion_value, order.total)
