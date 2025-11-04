from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from eshop.models import Order, OrderItem, Customer, Product, Category


class Command(BaseCommand):
    help = "Create default roles/groups and assign permissions"

    def handle(self, *args, **options):
        # Ensure content types exist
        models = [Order, OrderItem, Customer, Product, Category]
        cts = {m: ContentType.objects.get_for_model(m) for m in models}

        # Manager: orders + customers (add/change/delete/view)
        manager, _ = Group.objects.get_or_create(name="manager")
        perms_manager = []
        for m in [Order, OrderItem, Customer]:
            ct = cts[m]
            for codename in ["add", "change", "delete", "view"]:
                p = Permission.objects.get(codename=f"{codename}_{m._meta.model_name}", content_type=ct)
                perms_manager.append(p)
        manager.permissions.set(perms_manager)
        self.stdout.write(self.style.SUCCESS("Configured 'manager' group"))

        # Content manager: products + categories (add/change/delete/view)
        content_manager, _ = Group.objects.get_or_create(name="content_manager")
        perms_cm = []
        for m in [Product, Category]:
            ct = cts[m]
            for codename in ["add", "change", "delete", "view"]:
                p = Permission.objects.get(codename=f"{codename}_{m._meta.model_name}", content_type=ct)
                perms_cm.append(p)
        content_manager.permissions.set(perms_cm)
        self.stdout.write(self.style.SUCCESS("Configured 'content_manager' group"))

        # Analyst: read-only across Order/OrderItem/Product/Category/Customer (view only)
        analyst, _ = Group.objects.get_or_create(name="analyst")
        perms_analyst = []
        for m in models:
            ct = cts[m]
            p = Permission.objects.get(codename=f"view_{m._meta.model_name}", content_type=ct)
            perms_analyst.append(p)
        analyst.permissions.set(perms_analyst)
        self.stdout.write(self.style.SUCCESS("Configured 'analyst' group"))

        self.stdout.write(self.style.SUCCESS("All roles configured."))
