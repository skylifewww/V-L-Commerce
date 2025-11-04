import io
import csv
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from eshop.models import Product, Customer, Order, OrderItem
from django.utils import timezone
from datetime import timedelta


class AdminBasicsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user("staff", password="pass", is_staff=True)
        # Ensure full admin access for action execution in tests
        self.staff.is_superuser = True
        self.staff.save()
        self.client.login(username="staff", password="pass")
        self.product = Product.objects.create(name="P1", sku="SKU1", price=10, stock=10, is_active=True)
        self.customer = Customer.objects.create(full_name="John Doe", phone="+1234567")
        self.order = Order.objects.create(customer=self.customer)
        self.item = OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)

    def test_dashboard_view(self):
        url = reverse("admin:eshop_dashboard")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("revenue", resp.context)

    def test_admin_action_export_csv(self):
        url = reverse("admin:eshop_order_changelist")
        data = {
            "action": "export_orders_to_csv",
            "_selected_action": [str(self.order.pk)],
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")

    def test_shipped_quantity_validation(self):
        # cannot reduce quantity below shipped
        self.item.shipped_quantity = 2
        self.item.save()
        self.item.quantity = 1
        with self.assertRaises(Exception):
            self.item.full_clean()


class RolesTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create users
        self.manager = User.objects.create_user("manager", password="pass", is_staff=True)
        self.content_manager = User.objects.create_user("content", password="pass", is_staff=True)
        self.analyst = User.objects.create_user("analyst", password="pass", is_staff=True)

        # Create groups and assign view/change permissions programmatically (avoid relying on command)
        manager_g, _ = Group.objects.get_or_create(name="manager")
        content_g, _ = Group.objects.get_or_create(name="content_manager")
        analyst_g, _ = Group.objects.get_or_create(name="analyst")

        # Collect permissions
        def grant(model, actions):
            for code in actions:
                perm = Permission.objects.get(codename=f"{code}_{model._meta.model_name}")
                yield perm

        # Manager: orders, orderitems, customers (all CRUD)
        for p in grant(Order, ["add", "change", "delete", "view"]): manager_g.permissions.add(p)
        for p in grant(OrderItem, ["add", "change", "delete", "view"]): manager_g.permissions.add(p)
        for p in grant(Customer, ["add", "change", "delete", "view"]): manager_g.permissions.add(p)

        # Content manager: products, categories (all CRUD)
        from eshop.models import Product, Category
        for p in grant(Product, ["add", "change", "delete", "view"]): content_g.permissions.add(p)
        for p in grant(Category, ["add", "change", "delete", "view"]): content_g.permissions.add(p)

        # Analyst: view only across all
        for model in (Order, OrderItem, Customer, Product, Category):
            for p in grant(model, ["view"]): analyst_g.permissions.add(p)

        # Assign users to groups
        self.manager.groups.add(manager_g)
        self.content_manager.groups.add(content_g)
        self.analyst.groups.add(analyst_g)

        # Some data
        self.product = Product.objects.create(name="P1", sku="SKU1", price=10, stock=100, is_active=True)
        self.customer = Customer.objects.create(full_name="Alice", phone="+1000000")
        self.order = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price=self.product.price)

    def test_manager_can_access_orders_admin(self):
        self.client.login(username="manager", password="pass")
        resp = self.client.get(reverse("admin:eshop_order_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_content_manager_cannot_access_orders_admin(self):
        self.client.login(username="content", password="pass")
        resp = self.client.get(reverse("admin:eshop_order_changelist"))
        self.assertIn(resp.status_code, (302, 403))

    def test_analyst_can_view_dashboard_but_cannot_execute_actions(self):
        self.client.login(username="analyst", password="pass")
        # Can view dashboard
        resp = self.client.get(reverse("admin:eshop_dashboard"))
        self.assertEqual(resp.status_code, 200)
        # Cannot perform order action
        url = reverse("admin:eshop_order_changelist")
        resp = self.client.post(url, {"action": "mark_orders_as_shipped", "_selected_action": [str(self.order.pk)]})
        self.assertIn(resp.status_code, (302, 403))


class ExportXlsxTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user("admin", password="pass", is_staff=True, is_superuser=True)
        self.client.login(username="admin", password="pass")
        self.product = Product.objects.create(name="P2", sku="SKU2", price=20, stock=10, is_active=True)
        self.customer = Customer.objects.create(full_name="Bob", phone="+2000000")
        self.order = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)

    def test_export_orders_to_xlsx(self):
        url = reverse("admin:eshop_order_changelist")
        resp = self.client.post(url, {"action": "export_orders_to_xlsx", "_selected_action": [str(self.order.pk)]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertTrue(len(resp.content) > 100)  # has some content


class DashboardMetricsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user("admin", password="pass", is_staff=True, is_superuser=True)
        self.client.login(username="admin", password="pass")
        self.p1 = Product.objects.create(name="A", sku="A1", price=5, stock=100, is_active=True)
        self.p2 = Product.objects.create(name="B", sku="B1", price=10, stock=100, is_active=True)
        self.customer = Customer.objects.create(full_name="Carol", phone="+3000000")

        # Create orders on different days
        now = timezone.now()
        for i in range(3):
            o = Order.objects.create(customer=self.customer, created_at=now - timedelta(days=i))
            OrderItem.objects.create(order=o, product=self.p1, quantity=1 + i, price=self.p1.price)
        # Extra items for top products
        o2 = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(order=o2, product=self.p2, quantity=5, price=self.p2.price)

    def test_dashboard_metrics_present_and_correct_types(self):
        resp = self.client.get(reverse("admin:eshop_dashboard"))
        self.assertEqual(resp.status_code, 200)
        ctx = resp.context
        self.assertIn("revenue", ctx)
        self.assertIn("orders_by_day", ctx)
        self.assertIn("top_products", ctx)
        # revenue should be numeric-ish string/Decimal
        self.assertTrue(ctx["revenue"] is not None)
        # orders_by_day should be list of dicts with keys day, cnt
        self.assertTrue(isinstance(ctx["orders_by_day"], list))
        if ctx["orders_by_day"]:
            self.assertTrue("day" in ctx["orders_by_day"][0] and "cnt" in ctx["orders_by_day"][0])
        # top_products contains product__name and qty
        self.assertTrue(isinstance(ctx["top_products"], list))
        if ctx["top_products"]:
            self.assertTrue("product__name" in ctx["top_products"][0] and "qty" in ctx["top_products"][0])
