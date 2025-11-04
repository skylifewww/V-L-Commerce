from decimal import Decimal
import os
import shutil
import tempfile
import unittest

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.conf import settings

from eshop.models import Category, Product, Customer, Order, OrderItem


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="test_media_") )
class TestCategoryModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Category.objects.create(name="Root", slug="root")
        cls.child = Category.objects.create(name="Child", slug="child", parent=cls.root)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # cleanup temp MEDIA_ROOT created by override_settings
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if media_root and os.path.isdir(media_root):
            shutil.rmtree(media_root, ignore_errors=True)

    def test_create_category_with_parent(self):
        leaf = Category.objects.create(name="Leaf", slug="leaf", parent=self.child)
        self.assertEqual(leaf.parent, self.child)
        self.assertEqual(self.child.parent, self.root)

    def test_slug_unique_within_parent_only(self):
        # Desired: same slug allowed under different parents, but not under the same parent
        a = Category.objects.create(name="A", slug="a")
        # seed child under parent a
        Category.objects.create(name="A Child 1", slug="dup", parent=a)
        # same slug under different parent should be allowed
        b_parent = Category.objects.create(name="B Parent", slug="b-parent")
        Category.objects.create(name="B Child", slug="dup", parent=b_parent)  # should be OK per spec
        # same slug under same parent should fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="A Child 2", slug="dup", parent=a)

    def test_str_returns_name(self):
        self.assertEqual(str(self.root), "Root")
        self.assertEqual(str(self.child), "Child")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="test_media_") )
class TestProductModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Electronics", slug="electronics")
        # Mock image
        cls.image = SimpleUploadedFile("phone.jpg", b"fakeimg", content_type="image/jpeg")
        cls.product = Product.objects.create(
            category=cls.cat,
            name="Phone",
            sku="SKU-001",
            price=Decimal("499.99"),
            description="Smartphone",
            stock=10,
            image=cls.image,
            is_active=True,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if media_root and os.path.isdir(media_root):
            shutil.rmtree(media_root, ignore_errors=True)

    def test_create_with_image(self):
        self.assertTrue(self.product.image)
        self.assertTrue(os.path.basename(self.product.image.name).endswith(".jpg"))

    def test_stock_field(self):
        self.assertEqual(self.product.stock, 10)
        self.product.stock = 3
        self.product.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_unique_sku(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    category=self.cat,
                    name="Another Phone",
                    sku="SKU-001",
                    price=Decimal("199.99"),
                )

    def test_is_available_method(self):
        # Desired: product.is_available -> is_active and stock > 0
        self.assertTrue(self.product.is_available())
        self.product.stock = 0
        self.product.save()
        self.assertFalse(self.product.is_available())

    def test_get_absolute_url(self):
        # Desired: Product provides its detail URL
        url = self.product.get_absolute_url()
        self.assertIsInstance(url, str)
        self.assertTrue(url)


class TestCustomerModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Customer.objects.create(
            full_name="Ivan Petrov",
            email="ivan@example.com",
            phone="+380501112233",
            address="Kyiv",
        )

    def test_create_customer(self):
        self.assertEqual(self.customer.full_name, "Ivan Petrov")
        self.assertEqual(self.customer.email, "ivan@example.com")
        self.assertEqual(self.customer.phone, "+380501112233")

    def test_email_validation(self):
        cust = Customer(full_name="Bad Email", email="not-an-email", phone="123")
        with self.assertRaises(ValidationError):
            cust.full_clean()

    def test_phone_validation(self):
        # Desired: phone must be validated by regex or library
        cust = Customer(full_name="Bad Phone", email="ok@example.com", phone="abc")
        with self.assertRaises(ValidationError):
            cust.full_clean()

    def test_orders_relation(self):
        o1 = Order.objects.create(customer=self.customer)
        o2 = Order.objects.create(customer=self.customer)
        self.assertEqual(self.customer.orders.count(), 2)
        self.assertIn(o1, self.customer.orders.all())
        self.assertIn(o2, self.customer.orders.all())


class TestOrderModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Customer.objects.create(full_name="Pavel", email="pavel@example.com", phone="+380555")
        cls.product1 = Product.objects.create(name="A", sku="SKU-A", price=Decimal("10.00"), stock=100)
        cls.product2 = Product.objects.create(name="B", sku="SKU-B", price=Decimal("5.50"), stock=100)

    def test_create_order(self):
        order = Order.objects.create(customer=self.customer)
        self.assertEqual(order.status, Order.Status.NEW)
        self.assertEqual(str(order), f"Order #{order.id}")

    def test_total_property(self):
        order = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(order=order, product=self.product1, quantity=2, price=self.product1.price)
        OrderItem.objects.create(order=order, product=self.product2, quantity=3, price=self.product2.price)
        self.assertEqual(order.total, Decimal("2") * Decimal("10.00") + Decimal("3") * Decimal("5.50"))

    def test_change_statuses(self):
        order = Order.objects.create(customer=self.customer)
        order.status = Order.Status.PAID
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        order.status = Order.Status.SHIPPED
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_business_logic_methods(self):
        # order.cancel() -> CANCELLED and restock items
        order = Order.objects.create(customer=self.customer)
        # create item which should deduct stock via signal
        start_stock = self.product1.stock
        OrderItem.objects.create(order=order, product=self.product1, quantity=4, price=self.product1.price)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, start_stock - 4)
        # cancel should restock
        order.cancel()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, start_stock)


class TestOrderItemModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(name="Widget", sku="SKU-W", price=Decimal("20.00"), stock=5)
        cls.customer = Customer.objects.create(full_name="Maria", email="maria@example.com", phone="+380777")
        cls.order = Order.objects.create(customer=cls.customer)

    def test_create_with_price_snapshot(self):
        item = OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price=self.product.price)
        # Change product price afterwards, snapshot should remain
        self.product.price = Decimal("25.00")
        self.product.save()
        item.refresh_from_db()
        self.assertEqual(item.price, Decimal("20.00"))

    def test_subtotal_calculation(self):
        item = OrderItem.objects.create(order=self.order, product=self.product, quantity=3, price=Decimal("7.25"))
        self.assertEqual(item.subtotal, Decimal("21.75"))

    def test_relation_to_product(self):
        item = OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)
        self.assertEqual(item.product, self.product)
        self.assertIn(item, self.product.order_items.all())

    def test_auto_stock_deduction_signal(self):
        # Desired: creating an OrderItem deducts from product.stock automatically via signal
        start_stock = self.product.stock
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, start_stock - 2)

    def test_validate_sufficient_stock(self):
        # Desired: cannot create item with quantity greater than stock
        with self.assertRaises(ValidationError):
            item = OrderItem(order=self.order, product=self.product, quantity=999, price=self.product.price)
            item.full_clean()

    def test_auto_price_snapshot_on_create(self):
        # Desired: price auto-copied from product on create when price not provided
        item = OrderItem.objects.create(order=self.order, product=self.product, quantity=1)
        self.assertEqual(item.price, self.product.price)
