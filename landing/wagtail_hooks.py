from wagtail import hooks
from django.db import transaction
from .models import ProductLandingPage, OrderSuccessPage


def _ensure_success_page(page: ProductLandingPage) -> None:
    if not isinstance(page, ProductLandingPage):
        return
    if page.success_page_id:
        return
    parent = page
    title = f"Success: {page.title}" if page.title else "Success"
    slug = f"{page.slug}-success"[:255] if page.slug else "success"
    with transaction.atomic():
        success = OrderSuccessPage(title=title, slug=slug)
        parent.add_child(instance=success)
        success.save_revision().publish()
        page.success_page = success
        page.save()


@hooks.register("after_create_page")
def auto_create_success_page(request, page):
    _ensure_success_page(page)


@hooks.register("after_edit_page")
def ensure_success_page_exists(request, page):
    _ensure_success_page(page)
