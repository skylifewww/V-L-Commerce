from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from .models import ProductLandingPage, OrderSuccessPage

# class ProductLandingPageViewSet(SnippetViewSet):
#     model = ProductLandingPage
#     menu_label = "Product Landing Pages"
#     menu_icon = "pick"
#     list_display = ("title", "product")
#     list_filter = ("product",)
#     search_fields = ("title",)

# class OrderSuccessPageViewSet(SnippetViewSet):
#     model = OrderSuccessPage
#     menu_label = "Order Success Pages"
#     menu_icon = "success"
#     list_display = ("title",)
#     search_fields = ("title",)

# Register both models
# register_snippet(ProductLandingPageViewSet)
# register_snippet(OrderSuccessPageViewSet)
