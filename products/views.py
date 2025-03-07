from typing import List, Optional
from django.db.models import Prefetch, QuerySet
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import (
    viewsets, 
    permissions, 
    filters, 
    status, 
    mixins
)
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.request import Request
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product, ProductImage
from .serializers import (
    CategorySerializer, 
    ProductSerializer, 
    ProductCreateSerializer, 
    ProductImageSerializer
)
from .filters import CategoryFilter, ProductFilter
from .utils import process_image

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only product owners to edit their products.

    Permissions:
        - Read operations (`GET`, `HEAD`, `OPTIONS`) are allowed for any user.
        - Write operations (`POST`, `PUT`, `PATCH`, `DELETE`) are restricted to the product owner.

    Example Usage:
        ```python
        permission_classes = [IsOwnerOrReadOnly]
        ```
    """
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission for the requested action.

        Args:
            request (Request): The HTTP request object.
            view (View): The Django REST framework view.
            obj (Product): The product instance being accessed.

        Returns:
            bool: `True` if the request is read-only or the user is the owner, else `False`.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the product
        return obj.seller == request.user
    


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])  # Only admin users can approve categories
def approve_category(request, pk):
    """
    API endpoint for approving a category.
    """
    category = get_object_or_404(Category, pk=pk)
    if category.is_approved:
        return Response({'message': 'Category is already approved.'}, status=400)
    
    category.is_approved = True
    category.save()
    return Response({'message': f"Category '{category.name}' approved successfully."})



class BaseProductManagementMixin:
    """
    Base mixin for managing product ownership and authorization.

    Methods:
        - `get_owner_queryset`: Filters products to include only those owned by the current user.
        - `check_product_ownership`: Ensures the authenticated user is the product owner.

    Example Usage:
        ```python
        class ProductViewSet(BaseProductManagementMixin, viewsets.ModelViewSet):
            ...
        ```
    """
    def get_owner_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Filter a queryset to include only products owned by the current user.

        Args:
            queryset (QuerySet): The initial queryset.

        Returns:
            QuerySet: The filtered queryset containing only the user’s products.
        """
        return queryset.filter(seller=self.request.user)

    def check_product_ownership(self, request, product: Product) -> None:
        """
        Ensure the authenticated user owns the specified product.

        Args:
            product (Product): The product instance to check.

        Raises:
            PermissionDenied: If the current user is not the owner.
        """
        if product.seller != request.user:
            raise permissions.PermissionDenied("You do not have permission to modify this product.")


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product categories.
    Supports
        - Listing and retrieving categories.
        - Filtering and ordering.
        - Retrieving all products within a category.
    Permissions
        - Any user can list (`list`) and retrieve (`retrieve`) categories.
        - Admin users are required for all other actions.
    Query Parameters
        - `search`: Search by name or description.
        - `ordering`: Sort by name or created_at.
    Actions
        - `products`: Retrieve all products in the category.
    Example Usage
        ```python
        GET /api/categories/
        GET /api/categories/{slug}/products/
        ```
    """
    queryset = Category.objects.prefetch_related('children', 'products')
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    filterset_class = CategoryFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def get_permissions(self):
        """
        Define the permissions for different actions.

        Returns:
            List[permissions.BasePermission]: A list of permission instances.
        """

        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    def perform_create(self, serializer):
        """
        Save a new category.
        Sets the `created_by` field to the current user and `is_approved` to `False`.
        """
        serializer.save(created_by=self.request.user, is_approved=False)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def pending_approval(self, request):
        """
        Retrieve all categories that are pending approval.
        Only accessible to users with `is_staff` set to `True`.
        Returns
            List[CategorySerializer]: A list of serialized categories.
        """
        pending_categories = Category.objects.filter(is_approved=False)
        serializer = self.get_serializer(pending_categories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, slug=None):
    
        """
        Approve a category.
        This action marks a category as approved and makes it visible to all users.
        :param request: The request object.
        :param slug: The slug of the category to approve.
        :return: A Response object with a success message.
        """
        category = self.get_object()
        category.is_approved = True
        category.save()
        return Response({"message": "Category approved successfully."})

    @action(detail=True, methods=['get'])
    def products(self, request: Request, *args, **kwargs):
        """
        Retrieve all products in the category.
        Applies additional filtering based on the following query parameters
        - `min_price`
        - `max_price`
        - `seller`
        - `farm_name`
        - `in_stock`
        - `show_all`
        - `ordering`

        :param request: The request object
        :param slug: The slug of the category
        :return: A list of products in the category, filtered by the query parameters
        """
        category = self.get_object()
        products = Product.objects.filter(
            category=category, 
            is_available=True
        ).select_related('seller', 'category')
        
        # Apply additional filtering
        product_filter = ProductFilter(request.GET, queryset=products)
        serializer = ProductSerializer(
            product_filter.qs, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)


class ProductViewSet(BaseProductManagementMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing products.

    Supports:
        - Listing, retrieving, creating, updating, and deleting products.
        - Filtering and ordering.
        - Managing product images.

    Permissions:
        - Open access to `list`, `retrieve`, `featured`, and `organic` actions.
        - Authentication required for `create`.
        - Ownership required for modifying a product.

    Example Usage:
        ```python
        GET /api/products/
        POST /api/products/
        ```
    """
    queryset = Product.objects.select_related("seller", "category").prefetch_related(
        Prefetch("images", queryset=ProductImage.objects.only("id", "image", "is_primary"))
    )
    lookup_field = "slug"
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'stock_quantity']

    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.

        If the action is one of create, update, or partial_update, the
        ProductCreateSerializer is used. Otherwise, the ProductSerializer
        is used.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return ProductSerializer

    def get_permissions(self):        
        """
        Determine the permissions required for the current action.

        Provides open access for 'list', 'retrieve', 'featured', and 'organic' actions.
        Requires authentication for 'create' action.
        Requires both authentication and ownership for all other actions.

        :return: A list of instantiated permission classes
        """

        if self.action in ["list", "retrieve", "featured", "organic"]:
            return [permissions.AllowAny()]
        elif self.action == "create":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]

    def perform_create(self, serializer):
        """
        Save the product with the authenticated user as the seller.

        :param serializer: The ProductCreateSerializer instance
        :return: The saved product
        """
        serializer.save(seller=self.request.user)

    @action(detail=False, methods=['get'])
    def my_products(self, request: Request):
        """
        Return a list of products owned by the authenticated user.

        This view is accessible through the 'my_products' action of the ProductViewSet.
        """
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        queryset = self.get_owner_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        serializer = self.get_serializer(
            page if page is not None else queryset, 
            many=True
        )
        
        return (
            self.get_paginated_response(serializer.data) 
            if page is not None 
            else Response(serializer.data)
        )

    @action(detail=True, methods=['POST'])
    def upload_images(self, request: Request, slug: Optional[str] = None):
        """
            Uploads images to the product with the given slug.

            The images to be uploaded should be sent in the request body as a list
            of files with key 'images'.

            The first image in the list will be set as the primary image of the
            product. The primary image is the image that is displayed on the
            product's detail page.

            If the authenticated user is not the owner of the product, an
            authentication error is returned.

            If the request contains no images, a bad request error is returned.

            If an error occurs during the image upload process, a server error is
            returned.

            :param request: The request object
            :param slug: The slug of the product
            :return: A response containing the uploaded images or an error message
        """
        product = self.get_object()
        self.check_product_ownership(product)

        images: List = request.FILES.getlist('images')
        if not images:
            return Response(
                {"detail": "No images provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                product_images = []
                for image in images:
                    processed_image = process_image(image)
                    product_images.append(
                        ProductImage(
                            product=product, 
                            image=processed_image,
                            is_primary=len(product_images) == 0
                        )
                    )
                
                ProductImage.objects.bulk_create(product_images)
                
            serializer = ProductImageSerializer(product_images, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {"detail": f"Image upload failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductImageViewSet(BaseProductManagementMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing product images.

    Supports:
        - Listing, retrieving, uploading, and deleting images.

    Permissions:
        - Open access for `list` and `retrieve`.
        - Authentication and ownership required for modifying images.

    Example Usage:
        ```python
        GET /api/product-images/
        POST /api/product-images/
        ```
    """
    queryset = ProductImage.objects.select_related('product')
    serializer_class = ProductImageSerializer

    def get_permissions(self):
        """
        Determine the permissions required for the current action.

        Allows any user to access the 'list' and 'retrieve' actions, 
        while restricting all other actions to authenticated users 
        and ensuring that they are the owner of the product.
        
        :return:
            List[permissions.BasePermission]: A list of permission instances.
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]

    def perform_create(self, serializer):
        """
        Perform the creation of a product image, ensuring the user owns the product.

        :param serializer: The ProductImageSerializer instance containing validated data
        :raises PermissionDenied: If the current user is not the owner of the product
        """

        product = serializer.validated_data['product']
        self.check_product_ownership(product)
        serializer.save()
