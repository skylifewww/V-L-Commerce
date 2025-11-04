from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.core.cache import cache

register = template.Library()

def _render_product_card(product):
    # Cache key uses product id and updated_at for invalidation
    updated = getattr(product, "updated_at", None)
    ver = updated.isoformat() if updated else "0"
    key = f"pcard:{product.pk}:{ver}"
    html = cache.get(key)
    if html is None:
        html = render_to_string("landing/tags/product_card.html", {"product": product})
        cache.set(key, html, 300)
    return html

@register.simple_tag
def render_product_grid(products, category_slug=None):
    if category_slug:
        products = [p for p in products if getattr(getattr(p, "category", None), "slug", None) == category_slug]
    html = "".join(_render_product_card(p) for p in products)
    return mark_safe(f"<div class='product-grid'>{html}</div>")
