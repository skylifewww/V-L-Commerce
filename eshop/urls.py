from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    OrderCreateView,
    OrderDetailView,
    SearchView,
    StockAjaxView,
)

app_name = "eshop"

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/category/<slug:category_slug>/", ProductListView.as_view(), name="product_list_by_category"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("order/create/", OrderCreateView.as_view(), name="order_create"),
    path("order/<uuid:order_id>/", OrderDetailView.as_view(), name="order_detail"),
    path("search/", SearchView.as_view(), name="search"),
    path("ajax/stock/<int:pk>/", StockAjaxView.as_view(), name="ajax_stock"),
]
