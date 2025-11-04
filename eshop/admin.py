from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.db.models import Count, Sum, F
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.contrib.admin import helpers as admin_helpers
from django.conf import settings
from simple_history.admin import SimpleHistoryAdmin
import csv
from .models import Product, Order, Category, Customer, OrderItem, OrderComment
from .forms import QuickOrderForm


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "quantity", "shipped_quantity", "price", "subtotal_display")
    readonly_fields = ("subtotal_display",)

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj: OrderItem):
        return obj.subtotal if obj and obj.pk else "-"

@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ("id", "name", "category", "price", "stock", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "sku", "category__name")
    list_editable = ("price", "stock", "is_active")

    actions = ("update_product_prices", "update_stock_levels",)

    class BulkAdjustForm(admin_helpers.ActionForm):
        percent = forms.DecimalField(required=False, initial=0, help_text="% to add (e.g. 5 or -10)")
        delta = forms.IntegerField(required=False, initial=0, help_text="Delta to add to stock")

    action_form = BulkAdjustForm

    @admin.action(description="Update product prices by %")
    def update_product_prices(self, request, queryset):
        try:
            percent = request.POST.get("percent")
            pct = Decimal(str(percent)) if percent not in (None, "") else Decimal("0")
        except Exception:
            pct = Decimal("0")
        multiplier = Decimal("1") + (pct / Decimal("100"))
        for p in queryset:
            if p.price is not None:
                new_price = (Decimal(p.price) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                p.price = new_price
                p.save(update_fields=["price"]) 

    @admin.action(description="Update stock levels by delta")
    def update_stock_levels(self, request, queryset):
        try:
            delta_raw = request.POST.get("delta")
            delta = int(delta_raw) if delta_raw not in (None, "") else 0
        except Exception:
            delta = 0
        for p in queryset:
            p.stock = max(0, (p.stock or 0) + delta)
            p.save(update_fields=["stock"]) 

class OrderCommentInline(admin.TabularInline):
    model = OrderComment
    extra = 0
    fields = ("author", "text", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin):
    list_display = ("id", "customer", "status", "created_at", "updated_at", "total_display")
    list_filter = ("status", "created_at")
    search_fields = ("customer__full_name", "customer__phone", "payment_reference")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, OrderCommentInline]
    actions = ("mark_orders_as_shipped", "export_orders_to_csv", "export_orders_to_xlsx")

    @admin.display(description="Total")
    def total_display(self, obj: Order):
        return obj.total

    @admin.action(description="Mark selected orders as shipped")
    def mark_orders_as_shipped(self, request, queryset):
        queryset.update(status=Order.Status.SHIPPED, updated_at=timezone.now())

    @admin.action(description="Export selected orders to CSV")
    def export_orders_to_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=orders.csv"
        writer = csv.writer(response)
        writer.writerow(["id", "customer", "status", "created_at", "updated_at", "total"]) 
        for order in queryset:
            writer.writerow([
                order.id,
                getattr(order.customer, "full_name", "-"),
                order.get_status_display(),
                order.created_at.isoformat(),
                order.updated_at.isoformat(),
                str(order.total),
            ])
        return response

    @admin.action(description="Export selected orders to XLSX")
    def export_orders_to_xlsx(self, request, queryset):
        from io import BytesIO
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Orders"
        ws.append(["ID", "Customer", "Status", "Created", "Updated", "Total"]) 
        for order in queryset:
            ws.append([
                order.id,
                getattr(order.customer, "full_name", "-"),
                order.get_status_display(),
                order.created_at.isoformat(),
                order.updated_at.isoformat(),
                str(order.total),
            ])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = "attachment; filename=orders.xlsx"
        return resp

@admin.register(Category)
class CategoryAdmin(SimpleHistoryAdmin):
    list_display = ("id", "indented_name", "slug", "parent")
    search_fields = ("name", "slug")
    list_select_related = ("parent",)

    @admin.display(description="Name")
    def indented_name(self, obj: Category) -> str:
        depth = 0
        p = obj.parent
        while p is not None and depth < 10:
            depth += 1
            p = p.parent
        return ("\u00A0" * 4 * depth) + obj.name

@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    list_display = ("id", "full_name", "phone", "email", "created_at", "order_count", "total_revenue")
    search_fields = ("full_name", "phone", "email")
    date_hierarchy = "created_at"

    @admin.display(description="Orders")
    def order_count(self, obj: Customer):
        return getattr(obj, "orders__count", None) or obj.orders.count()

    @admin.display(description="Revenue")
    def total_revenue(self, obj: Customer):
        agg = obj.orders.aggregate(
            total=Sum(F("items__price") * F("items__quantity"), output_field=models.DecimalField(max_digits=12, decimal_places=2))
        )
        return agg.get("total") or 0

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price")


# ----- Custom Admin Dashboard -----
def _get_dashboard_context():
    now = timezone.now()
    last_30 = now - timezone.timedelta(days=30)
    orders_qs = Order.objects.filter(created_at__gte=last_30)
    revenue_agg = orders_qs.aggregate(
        total=Sum(F("items__price") * F("items__quantity"), output_field=models.DecimalField(max_digits=12, decimal_places=2))
    )
    top_products = (
        OrderItem.objects.filter(order__created_at__gte=last_30)
        .values("product__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:10]
    )
    by_day = (
        orders_qs
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(cnt=Count("id"))
        .order_by("day")
    )
    threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    low_stock = Product.objects.filter(is_active=True, stock__lte=threshold).order_by("stock")[:20]
    pending_orders = Order.objects.exclude(status=Order.Status.SHIPPED).order_by("-created_at")[:20]
    return {
        "revenue": revenue_agg.get("total") or 0,
        "orders_by_day": list(by_day),
        "top_products": list(top_products),
        "low_stock": list(low_stock.values("id", "name", "stock")),
        "pending_orders": list(pending_orders.values("id", "status", "created_at")),
    }


@staff_member_required
def admin_dashboard_view(request):
    from django.shortcuts import render

    ctx = _get_dashboard_context()
    return render(request, "admin/eshop_dashboard.html", ctx)


def get_custom_admin_urls(urls):
    def _get_urls():
        my_urls = [
            path("eshop/dashboard/", admin.site.admin_view(admin_dashboard_view), name="eshop_dashboard"),
        ]
        return my_urls + urls()

    return _get_urls


# Patch admin site to add our dashboard URL
admin.site.get_urls = get_custom_admin_urls(admin.site.get_urls)


# ----- Quick Order creation (via admin view) -----
@staff_member_required
def quick_order_view(request):
    from django.shortcuts import render, redirect
    from django.contrib import messages

    if request.method == "POST":
        form = QuickOrderForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data["product"]
            qty = form.cleaned_data["quantity"]
            cust, _ = Customer.objects.get_or_create(
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data["phone"],
                defaults={
                    "email": form.cleaned_data.get("email", ""),
                    "address": form.cleaned_data.get("address", ""),
                },
            )
            order = Order.objects.create(customer=cust, shipping_address=cust.address)
            OrderItem.objects.create(order=order, product=product, quantity=qty, price=product.price)
            messages.success(request, f"Order #{order.id} created")
            return redirect("admin:eshop_order_change", order.pk)
    else:
        form = QuickOrderForm()
    return render(request, "admin/quick_order.html", {"form": form})


def get_more_admin_urls(urls):
    def _get_urls():
        my_urls = [
            path("eshop/quick-order/", admin.site.admin_view(quick_order_view), name="eshop_quick_order"),
        ]
        return my_urls + urls()

    return _get_urls


admin.site.get_urls = get_more_admin_urls(admin.site.get_urls)
