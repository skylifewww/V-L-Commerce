from typing import Any, Dict, List
from django import forms
from django.core.exceptions import ValidationError
from .models import Customer, Product
import json
import ast


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["full_name", "email", "phone", "address"]


class AnyJSONField(forms.Field):
    def to_python(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, (dict, list)):
            return value
        s = str(value).strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            try:
                return ast.literal_eval(s)
            except Exception:
                return s


class OrderForm(forms.Form):
    customer_data = AnyJSONField()
    shipping_address = forms.CharField(widget=forms.Textarea, required=False)
    products = AnyJSONField(help_text="List of items: [{product_id, quantity}, ...]")

    def _parse_json_or_literal(self, raw: str):
        if isinstance(raw, (dict, list)):
            return raw
        if raw is None:
            return None
        s = raw if isinstance(raw, str) else str(raw)
        s = s.strip()
        if not s:
            return None
        # Try JSON first
        try:
            return json.loads(s)
        except Exception:
            pass
        # Fallback to Python literal (for tests posting python repr)
        try:
            return ast.literal_eval(s)
        except Exception:
            return None

    def clean_products(self) -> List[Dict[str, Any]]:
        items = self.cleaned_data["products"]
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list) or not items:
            raise ValidationError("Provide a non-empty list of products.")
        product_ids = [int(i.get("product_id", 0)) for i in items if str(i.get("product_id")).isdigit()]
        qty_by_id: Dict[int, int] = {}
        for i in items:
            try:
                pid = int(i.get("product_id"))
                qty = int(i.get("quantity", 0))
            except Exception:
                raise ValidationError("Invalid product item format.")
            if qty <= 0:
                raise ValidationError("Quantity must be positive.")
            qty_by_id[pid] = qty_by_id.get(pid, 0) + qty
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids, is_active=True)}
        missing = [pid for pid in qty_by_id.keys() if pid not in products]
        if missing:
            raise ValidationError(f"Products not found: {missing}")
        for pid, qty in qty_by_id.items():
            p = products[pid]
            if qty > (p.stock or 0):
                raise ValidationError(f"Insufficient stock for product {p.name} (requested {qty}, available {p.stock}).")
        # Return normalized list including product objects
        normalized = [{"product": products[int(i["product_id"])], "quantity": int(i["quantity"])} for i in items]
        return normalized

    def clean_customer_data(self) -> Dict[str, Any]:
        data = self.cleaned_data["customer_data"]
        if not isinstance(data, dict):
            raise ValidationError("Invalid customer_data format.")
        required = ["full_name", "phone"]
        for key in required:
            if not data.get(key):
                raise ValidationError({key: "This field is required."})
        return data


class QuickOrderForm(forms.Form):
    product_id = forms.IntegerField()
    quantity = forms.IntegerField(min_value=1, initial=1)
    full_name = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=32)
    email = forms.EmailField(required=False)
    address = forms.CharField(required=False)

    def clean(self):
        cleaned = super().clean()
        pid = cleaned.get("product_id")
        qty = cleaned.get("quantity")
        if pid is None or qty is None:
            return cleaned
        try:
            product = Product.objects.get(pk=pid, is_active=True)
        except Product.DoesNotExist:
            raise ValidationError("Product does not exist.")
        if qty > (product.stock or 0):
            raise ValidationError("Insufficient stock.")
        cleaned["product"] = product
        return cleaned
