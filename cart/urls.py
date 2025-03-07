from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('add/<int:product_id>/', views.CartAddProductView.as_view(), name='cart_add'),
    path('remove/<int:product_id>/', views.CartRemoveProductView.as_view(), name='cart_remove'),
    path('details/', views.CartDetailView.as_view(), name='cart_detail'),
]
