from django.urls import path
from . import views

app_name = 'landing'

urlpatterns = [
    path('api/product/<int:product_id>/', views.product_api, name='product_api'),
]
