from django.urls import path
from .views import OrderCreateAPIView, UserOrderListAPIView
app_name = 'orders'
urlpatterns = [
path('create/', OrderCreateAPIView.as_view(), name='order_create'),
path('list/', UserOrderListAPIView.as_view(), name='order_list'),
]