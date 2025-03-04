from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .filters import CategoryFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of a product to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the product
        return obj.seller == request.user



class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product categories.
    - Anyone can view categories.
    - Only admins can create, update, or delete categories.
    - Farmers select from available categories when uploading products.
    """
    queryset = Category.objects.all().select_related('parent').prefetch_related('children').order_by('-created_at')
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    # Search, filter, and ordering support
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    filterset_cass = CategoryFilter
    ordering = ['-created_at']  # Default: Newest categories first

    def get_permissions(self):
        """
        Allow read access to everyone, but restrict modifications to admins.
        """
        if self.action in ['list', 'retrieve']:  # Viewing allowed for all
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]  # Modifications restricted to admins

    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """
        Retrieve all available products under a specific category.
        """
        category = self.get_object()
        products = Product.objects.filter(category=category, is_available=True).select_related('seller', 'category').prefetch_related('images')
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

