from django.db import models, transaction
import uuid
from decimal import Decimal
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from simple_history.models import HistoricalRecords
import requests
from wagtail.snippets.models import register_snippet


@register_snippet
class Product(models.Model):
    category = models.ForeignKey(
        "Category",
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/%Y/%m/%d", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    def is_available(self) -> bool:
        """Product is available if it is active and has stock > 0."""
        return bool(self.is_active and self.stock > 0)

    def get_absolute_url(self) -> str:
        """Return a simple detail URL path; avoids dependency on URLConf in tests."""
        return f"/products/{self.pk}/"


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ("slug", "parent")

    def __str__(self) -> str:
        return self.name


class Customer(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(
        max_length=32,
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9\-\s\(\)]{7,20}$",
                message="Enter a valid phone number.",
            )
        ],
    )
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.full_name


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        CANCELLED = "cancelled", "Cancelled"

    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer = models.ForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    shipping_address = models.TextField(blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    # Analytics compatibility fields
    tiktok_source = models.CharField(max_length=128, blank=True)
    conversion_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self) -> str:
        return f"Order #{self.id}"

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))

    def cancel(self) -> None:
        """Cancel order and restock items once."""
        if self.status == self.Status.CANCELLED:
            return
        if self.status == self.Status.SHIPPED:
            raise ValidationError("Cannot cancel an order that has been shipped.")
        with transaction.atomic():
            # Restock products
            for item in self.items.select_related("product"):
                product = item.product
                product.stock = (product.stock or 0) + item.quantity
                product.save(update_fields=["stock"]) 
            self.status = self.Status.CANCELLED
            self.save(update_fields=["status", "updated_at"]) 


class Lead(models.Model):
    order = models.OneToOneField("Order", on_delete=models.CASCADE, related_name="lead")
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    product_id = models.IntegerField()
    quantity = models.IntegerField(default=1)
    utm_source = models.CharField(max_length=64, blank=True)
    utm_medium = models.CharField(max_length=64, blank=True)
    utm_campaign = models.CharField(max_length=128, blank=True)
    ttclid = models.CharField(max_length=128, blank=True)
    fbp = models.CharField(max_length=128, blank=True)
    fbc = models.CharField(max_length=128, blank=True)
    landing_url = models.URLField(blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Lead for Order #{self.order_id}"

class OrderComment(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Comment #{self.id} on Order #{self.order_id}"


@receiver(post_save, sender=Order)
def notify_new_order(sender, instance: "Order", created: bool, **kwargs):
    if not created:
        return
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        msg = f"New order #{instance.id}. Status: {instance.get_status_display()}"
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=5,
        )
    except Exception:
        # Fail silently
        pass


class OrderItem(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("Product", on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    shipped_quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self) -> str:
        return f"{self.product} x{self.quantity}"

    @property
    def subtotal(self) -> Decimal:
        return (self.price or Decimal("0.00")) * Decimal(self.quantity)

    def clean(self) -> None:
        # Ensure sufficient stock
        if self.product_id and self.quantity:
            # fetch latest stock
            product = self.product if hasattr(self, "product") else None
            if product is None and self.product_id:
                product = Product.objects.filter(pk=self.product_id).first()
            if product and product.stock is not None and self.quantity > product.stock:
                raise ValidationError({"quantity": "Insufficient stock for the requested quantity."})
        # Business rule: cannot reduce below shipped
        if self.quantity is not None and self.shipped_quantity is not None and self.quantity < self.shipped_quantity:
            raise ValidationError({"quantity": "Quantity cannot be less than already shipped."})

    def save(self, *args, **kwargs):
        # Auto-snapshot price from product if not provided
        if self.price is None and self.product_id:
            # ensure product is loaded
            prod = getattr(self, "product", None)
            if prod is None:
                prod = Product.objects.get(pk=self.product_id)
            self.price = prod.price
        super().save(*args, **kwargs)


@receiver(post_save, sender=OrderItem)
def deduct_stock_on_order_item_create(sender, instance: "OrderItem", created: bool, **kwargs):
    if not created:
        return
    product = instance.product
    if product and instance.quantity:
        # do not go negative; assume validation prevented it
        new_stock = max(0, (product.stock or 0) - instance.quantity)
        if new_stock != product.stock:
            product.stock = new_stock
            product.save(update_fields=["stock"]) 


@receiver(pre_save, sender=OrderItem)
def adjust_stock_on_order_item_update(sender, instance: "OrderItem", **kwargs):
    if not instance.pk:
        # handled by post_save(create)
        return
    try:
        prev = OrderItem.objects.select_related("product").get(pk=instance.pk)
    except OrderItem.DoesNotExist:
        return
    # If product changes, return old qty to old product and deduct new qty from new product
    if prev.product_id != instance.product_id:
        if prev.product:
            prev.product.stock = (prev.product.stock or 0) + prev.quantity
            prev.product.save(update_fields=["stock"]) 
        if instance.product:
            # ensure enough stock for new product and quantity
            if instance.quantity > (instance.product.stock or 0):
                raise ValidationError({"quantity": "Insufficient stock for the requested quantity."})
            instance.product.stock = (instance.product.stock or 0) - instance.quantity
            instance.product.save(update_fields=["stock"]) 
        return
    # Business rule: cannot reduce below shipped
    if instance.quantity < (prev.shipped_quantity or 0):
        raise ValidationError({"quantity": "Quantity cannot be less than already shipped."})
    # Same product; adjust by delta
    delta = int(instance.quantity) - int(prev.quantity)
    if delta == 0:
        return
    if delta > 0:
        # need to deduct additional quantity
        if delta > (instance.product.stock or 0):
            raise ValidationError({"quantity": "Insufficient stock for the requested quantity."})
        instance.product.stock = (instance.product.stock or 0) - delta
        instance.product.save(update_fields=["stock"]) 
    else:
        # quantity decreased -> return (-delta)
        instance.product.stock = (instance.product.stock or 0) + (-delta)
        instance.product.save(update_fields=["stock"]) 


@receiver(post_delete, sender=OrderItem)
def restock_on_order_item_delete(sender, instance: "OrderItem", **kwargs):
    product = instance.product
    if product and instance.quantity:
        product.stock = (product.stock or 0) + instance.quantity
        product.save(update_fields=["stock"]) 
