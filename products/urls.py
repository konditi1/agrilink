from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, ProductImageViewSet,  ProductDetailView, approve_category

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-images', ProductImageViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/categories/<int:pk>/approve/', approve_category, name='approve-category'), 
    path('api/product/<int:id>/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
]