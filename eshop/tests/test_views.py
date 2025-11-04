from decimal import Decimal
from uuid import uuid4
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from eshop.models import Product, Category, Customer, Order, OrderItem


class ViewSetupMixin:
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Cat", slug="cat")
        cls.p1 = Product.objects.create(name="P1", sku="SKU1", price=Decimal("10.00"), stock=5, category=cls.cat)
        cls.p2 = Product.objects.create(name="P2", sku="SKU2", price=Decimal("20.00"), stock=0)
        cls.customer = Customer.objects.create(full_name="Ivan", phone="+123")


class TestProductViews(ViewSetupMixin, TestCase):
    def test_product_list_status_and_context(self):
        url = reverse("eshop:product_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("products", resp.context)
        self.assertContains(resp, self.p1.name)

    def test_product_list_by_category(self):
        url = reverse("eshop:product_list_by_category", kwargs={"category_slug": self.cat.slug})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.p1.name)

    def test_product_detail(self):
        url = reverse("eshop:product_detail", kwargs={"pk": self.p1.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["product"].id, self.p1.id)

    def test_search(self):
        url = reverse("eshop:search") + "?q=P1"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.p1.name)

    def test_ajax_stock(self):
        url = reverse("eshop:ajax_stock", kwargs={"pk": self.p1.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {"product_id": self.p1.id, "stock": self.p1.stock})


class TestOrderViews(ViewSetupMixin, TestCase):
    def test_order_create_success(self):
        url = reverse("eshop:order_create")
        payload = {
            "customer_data": {"full_name": "Ivan", "phone": "+123"},
            "shipping_address": "Address",
            "products": [{"product_id": self.p1.id, "quantity": 2}],
        }
        resp = self.client.post(url, data={
            "customer_data": payload["customer_data"],
            "shipping_address": payload["shipping_address"],
            "products": payload["products"],
        }, content_type="application/json")
        # Django's FormView expects form-encoded; we send JSON by fields
        # Use regular POST with JSONField accepting dict/list
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 302)
        # redirected to order detail
        self.assertIn(reverse("eshop:order_detail", kwargs={"order_id": Order.objects.last().uid}), resp["Location"]) 

    def test_order_create_insufficient_stock(self):
        url = reverse("eshop:order_create")
        payload = {
            "customer_data": {"full_name": "Ivan", "phone": "+123"},
            "shipping_address": "Address",
            "products": [{"product_id": self.p1.id, "quantity": 999}],
        }
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Failed to create order", status_code=200)

    def test_order_detail_status(self):
        order = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(order=order, product=self.p1, quantity=1, price=self.p1.price)
        url = reverse("eshop:order_detail", kwargs={"order_id": order.uid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, str(order.total))

    def test_order_detail_not_found(self):
        url = reverse("eshop:order_detail", kwargs={"order_id": uuid4()})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
