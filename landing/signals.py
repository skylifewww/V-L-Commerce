from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction, connection

from wagtail.models import Site

from eshop.models import Product
from .models import HomePage, ProductListingPage, ProductDetailPage


def _get_parent_page():
    site = Site.objects.select_related("root_page").order_by("-is_default_site").first()
    if not site:
        return None
    root = site.root_page.specific
    # Prefer first ProductListingPage under root
    listing = root.get_children().type(ProductListingPage).first()
    if listing:
        return listing.specific
    # Else allow HomePage
    if isinstance(root, HomePage):
        return root
    return root  # fallback to root even if not HomePage


@receiver(post_save, sender=Product)
def ensure_product_detail_page(sender, instance: Product, created: bool, **kwargs):
    # Page tree operations
    def _op():
        parent = _get_parent_page()
        if not parent:
            return
        # Already has a detail page?
        existing = getattr(instance, "detail_pages", None)
        if created:
            if existing and existing.exists():
                page = existing.first()
            else:
                page = ProductDetailPage(title=instance.name, product=instance)
                parent.add_child(instance=page)
                rev = page.save_revision()
                rev.publish()
                return
        # On update: sync all linked pages
        if existing:
            for page in existing.all():
                page.title = instance.name
                page.seo_title = instance.name
                # slug sync via clean() during revision save
                rev = page.save_revision()
                rev.publish()
    # Run immediately to keep behavior deterministic in tests/dev
    _op()
