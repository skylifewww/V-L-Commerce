from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.core.cache import cache
from urllib.parse import urlparse, parse_qs
import re

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

@register.filter(name="youtube_id")
def youtube_id(value):
    if not value:
        return ""
    s = str(value).strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
        return s
    try:
        u = urlparse(s)
    except Exception:
        return s
    host = (u.hostname or "").lower()
    if host.endswith("youtu.be"):
        segs = [p for p in u.path.split("/") if p]
        return segs[0] if segs else ""
    if "youtube.com" in host:
        if u.path.startswith("/watch"):
            v = parse_qs(u.query).get("v", [""])[0]
            return v
        if u.path.startswith("/embed/"):
            return u.path.split("/")[2] if len(u.path.split("/")) > 2 else ""
        if u.path.startswith("/shorts/"):
            return u.path.split("/")[2] if len(u.path.split("/")) > 2 else ""
    m = re.search(r"v=([A-Za-z0-9_-]{11})", s)
    if m:
        return m.group(1)
    m = re.search(r"([A-Za-z0-9_-]{11})", s)
    return m.group(1) if m else s
