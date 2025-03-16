from typing import List, Optional
from django.db.models import Prefetch, QuerySet
from django.db import transaction
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import APIException, PermissionDenied
from django.shortcuts import get_object_or_404

from rest_framework import (
    viewsets, 
    permissions, 
    filters, 
    status, 
    mixins
)
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
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
from cart.serializers import CartAddProductSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

logger = logging.getLogger(__name__)

class ProductOwnershipException(APIException):
    status_code = 403
    default_detail = "You do not have permission to modify this product."
    default_code = "permission_denied"


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only product owners to edit their products.
    Permissions
        - Read operations (`GET`, `HEAD`, `OPTIONS`) are allowed for any user.
        - Write operations (`POST`, `PUT`, `PATCH`, `DELETE`) are restricted to the product owner.
    Example Usage
        ```python
        permission_classes = [IsOwnerOrReadOnly]
        ```
    """
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission for the requested action.
        Args
            request (Request): The HTTP request object.
            view (View): The Django REST framework view.
            obj (Product): The product instance being accessed.
        Returns
            bool: `True` if the request is read-only or the user is the owner, else `False`.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the product
        return obj.product.seller == request.user
    


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])  # Only admin users can approve categories
def approve_category(request, pk):
   
    """
    Approve a category if it has not been approved yet.
    
    This endpoint allows an admin user to approve a category that is still pending approval.

    ---
    **Permissions**: Admin only  
    **Method**: POST  
    **URL**: `/api/categories/{id}/approve/`  

    ### Request Parameters
    - `id` (**path parameter**): The primary key (ID) of the category to approve.

    ### Responses
    - **200 OK**: ✅ Category successfully approved.
    - **400 Bad Request**: ❌ The category is already approved.
    - **404 Not Found**: ❌ Category does not exist.

    ### Example Request
    ```http
    POST /api/categories/5/approve/
    ```

    ### Example Response (Success)
    ```json
    {
        "message": "Category 'Fruits' approved successfully."
    }
    ```

    ### Example Response (Already Approved)
    ```json
    {
        "message": "Category is already approved."
    }
    ```

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
    Methods
        - `get_owner_queryset`: Filters products to include only those owned by the current user.
        - `check_product_ownership`: Ensures the authenticated user is the product owner.
    Example Usage
        ```python
        class ProductViewSet(BaseProductManagementMixin, viewsets.ModelViewSet):
            ...
        ```
    """
    def get_owner_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Filter a queryset to include only products owned by the current user.
        Args
            queryset (QuerySet): The initial queryset.
        Returns
            QuerySet: The filtered queryset containing only the user’s products.
        """
        return queryset.filter(seller=self.request.user)

    def check_product_ownership(self, request, product: Product) -> None:
        """
        Ensure the authenticated user owns the specified product.
        Args
            product (Product): The product instance to check.
        Raises
            PermissionDenied: If the current user is not the owner.
        """
        if product.seller != request.user:
            raise ProductOwnershipException



class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing product categories.

    - **list**: Retrieve all categories.
    - **retrieve**: Get details of a specific category.
    - **create**: Add a new category (Admin only).
    - **update**/**partial_update**: Modify an existing category (Admin only).
    - **delete**: Remove a category (Admin only).
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
        Returns
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
    @swagger_auto_schema(
        operation_summary="Retrieve All Categories",
        operation_description="""
        Returns a list of all product categories. 
        
        - **Supports filtering** by name and description.
        - **Supports ordering** by name and creation date.
        - Categories include preloaded **child categories** and associated **products**.
        """,
        responses={200: CategorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a Specific Category",
        operation_description="""
        Fetches details of a specific category using its slug.

        - **Includes child categories** if applicable.
        - **Includes associated products** related to this category.
        """,
        manual_parameters=[
            openapi.Parameter(
                name="slug",
                in_=openapi.IN_PATH,
                description="The unique slug identifier of the category.",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: CategorySerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a New Category",
        operation_description="""
        Adds a new product category to the system.
        
        - **Requires Admin access**.
        - The `slug` is automatically generated from the category name.
        - The category remains **pending approval** until an admin approves it.
        """,
        request_body=CategorySerializer,
        responses={
            201: CategorySerializer(),
            400: openapi.Response(
                description="Invalid input data",
                examples={"application/json": {"error": "Category with this name already exists."}}
            )
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a Category",
        operation_description="""
        Fully updates an existing category.

        - **Requires Admin access**.
        - Overwrites all category fields with new data.
        """,
        request_body=CategorySerializer,
        responses={200: CategorySerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update a Category",
        operation_description="""
        Updates specific fields of an existing category.

        - **Requires Admin access**.
        - Use this endpoint to update only selected fields instead of overwriting all data.
        """,
        request_body=CategorySerializer,
        responses={200: CategorySerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Category",
        operation_description="""
        Removes an existing category permanently.

        - **Requires Admin access**.
        - **Warning:** Deleting a category will also remove associated products unless handled otherwise.
        """,
        responses={
            204: openapi.Response(
                description="Category deleted successfully",
                examples={"application/json": {"message": "Category deleted successfully."}}
            ),
            404: openapi.Response(
                description="Category not found",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve All Categories Pending Approval",
        operation_description="""
        Returns a list of categories that are waiting for admin approval.

        - **Requires Admin access**.
        - Categories listed here are not yet visible to regular users.
        """,
        responses={200: CategorySerializer(many=True)}
    )
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

    @swagger_auto_schema(
        operation_summary="Approve a category",
        operation_description="""
        Approves a category by its slug, making it visible to all users.

        **Permissions:**  
        - Admin only (`IsAdminUser`)

        **Path Parameter:**  
        - `slug` (string, required): The unique identifier for the category to approve.

        **Responses:**  
        - `200 OK`: Category approved successfully.  
        - `404 Not Found`: If the category with the given slug does not exist.
        """,
        responses={
            200: openapi.Response(
                description="Category approved successfully",
                examples={"application/json": {"message": "Category approved successfully."}}
            ),
            404: openapi.Response(
                description="Category not found",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
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

    @swagger_auto_schema(
        operation_summary="Retrieve products in a category",
        operation_description="Returns all products within a given category, with optional filters.",
        manual_parameters=[
            openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price filter", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price filter", type=openapi.TYPE_NUMBER),
            openapi.Parameter('seller', openapi.IN_QUERY, description="Filter by seller ID", type=openapi.TYPE_STRING),
            openapi.Parameter('farm_name', openapi.IN_QUERY, description="Filter by farm name", type=openapi.TYPE_STRING),
            openapi.Parameter('in_stock', openapi.IN_QUERY, description="Filter by stock availability", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('show_all', openapi.IN_QUERY, description="Show all products including unavailable ones", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Order by fields (e.g., price, name)", type=openapi.TYPE_STRING),
        ],
        responses={200: ProductSerializer(many=True)}
    )
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
    
    @swagger_auto_schema(
        operation_summary="Retrieve Featured Products",
        operation_description="""
        Returns a list of featured products.
        
        **Criteria for featuring:**
        - Products manually marked as "featured".
        - Products with high ratings, sales, or popularity.
        """,
        responses={200: ProductSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Returns a list of featured products.
        """
        featured_products = self.get_queryset().filter(is_featured=True)

        page = self.paginate_queryset(featured_products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(featured_products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductViewSet(BaseProductManagementMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing products.

    **Features:**
    - List, retrieve, create, update, delete products.
    - Supports filtering, searching, and ordering.
    - Manage product images.

    **Permissions:**
    - Open access: `list`, `retrieve`, `featured`, `organic`.
    - Authentication required: `create`.
    - Ownership required: Modify or delete a product.

    **Example Usage:**
    ```http
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
    
    @swagger_auto_schema(
        operation_summary="Retrieve All Products",
        operation_description="""
        Returns a list of all products available in the marketplace.
        
        **Filters & Ordering:**
        - **Search**: `name`, `description`
        - **Filter by**: `category`, `price range`
        - **Sort by**: `price`, `created_at`, `stock_quantity`
        """,
        responses={200: ProductSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a Specific Product",
        operation_description="Fetches details of a specific product using its slug.",
        manual_parameters=[
            openapi.Parameter(
                name="slug",
                in_=openapi.IN_PATH,
                description="The unique slug identifier of the product.",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={200: ProductSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a New Product",
        operation_description="""
        Allows an authenticated user to create a new product in the marketplace.

        **Requirements:**
        - **Authentication required**.
        - The authenticated user is set as the seller.
        - The unit of measurement must be one of the following:
        
        **Weight-based:** kg, g, mg, lb, oz  
        **Volume-based:** l, ml, gal, pt, qt  
        **Count-based:** pcs, dozen, half_dozen, pair, bundle  
        **Container-based:** box, bag, crate, basket, jar, bottle  
        **Special units:** bunch, head, stick, clove, slice  

        **Important Notes:**
        -can be []or models.ImageField(upload_to='product_images/')

        """,
        request_body=ProductCreateSerializer,
        responses={
            201: openapi.Response(
                description="Product successfully created",
                schema=ProductSerializer
            ),
            400: openapi.Response(
                description="Invalid input",
                examples={
                    "application/json": {"error": "Product name already exists."}
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                examples={
                    "application/json": {"detail": "Authentication credentials were not provided."}
                }
            ),
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Handles product creation, ensuring the authenticated user is the seller.
        """
        return super().create(request, *args, **kwargs)


    @swagger_auto_schema(
        operation_summary="Update an Existing Product",
        operation_description="Fully updates an existing product. **Only the owner can modify it.**",
        request_body=ProductCreateSerializer,
        responses={200: ProductSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update a Product",
        operation_description="Updates specific fields of a product. **Only the owner can modify it.**",
        request_body=ProductCreateSerializer,
        responses={200: ProductSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Product",
        operation_description="Deletes an existing product. **Only the owner can delete it.**",
        responses={
            204: openapi.Response(description="Product deleted successfully"),
            404: openapi.Response(
                description="Product not found",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve My Products",
        operation_description="""
        Returns a list of products owned by the authenticated user.

        - **Requires authentication**.
        - If the user is not authenticated, returns a `401 Unauthorized` error.
        """,
        responses={
            200: ProductSerializer(many=True),
            401: openapi.Response(
                description="Authentication required",
                examples={"application/json": {"detail": "Authentication required"}}
            )
        }
    )

    @action(detail=False, methods=['get'])
    def my_products(self, request: Request):
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
    
    @swagger_auto_schema(
        operation_summary="Upload Product Images",
        operation_description="""
        Upload images for a product.

        - The first uploaded image will be set as the **primary image**.
        - **Only the product owner can upload images**.
        """,
        manual_parameters=[
            openapi.Parameter(
                name="images",
                in_=openapi.IN_FORM,
                description="One or more images to upload",
                type=openapi.TYPE_FILE,
                required=True,
            ),
        ],
        responses={
            201: ProductImageSerializer(many=True),
            400: openapi.Response(
                description="No images provided",
                examples={"application/json": {"detail": "No images provided"}}
            ),
            500: openapi.Response(
                description="Image upload failed",
                examples={"application/json": {"detail": "Image upload failed: [error_message]"}}
            ),
        },
        consumes=["multipart/form-data"],
    )
    @action(detail=True, methods=['POST'], parser_classes=[MultiPartParser])
    def upload_images(self, request: Request, slug: Optional[str] = None):
        try:
            product = get_object_or_404(Product, slug=slug)
            self.check_product_ownership(request, product)

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
                        try:
                            processed_image = process_image(image)
                        except Exception as e:
                            logger.error(f"Failed to process image: {str(e)}")
                            return Response(
                                {"detail": f"Invalid image: {str(e)}"}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
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
        
        except PermissionDenied:
            return Response(
                {"detail": "You do not have permission to upload images for this product."},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {"detail": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ProductImageViewSet(BaseProductManagementMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing product images.

    ## Features:
    - **List Images**: Retrieve all product images.
    - **Retrieve Image**: Get details of a specific image.
    - **Upload Image**: Authenticated users can upload images for their products.
    - **Delete Image**: Owners can delete images of their products.

    ## Permissions:
    - ✅ `list`, `retrieve`: Public access.
    - 🔒 `create`, `update`, `delete`: Only the product owner.

    ## Example Usage:
    - **List all images**: `GET /api/product-images/`
    - **Retrieve an image**: `GET /api/product-images/{id}/`
    - **Upload a new image**: `POST /api/product-images/`
    - **Delete an image**: `DELETE /api/product-images/{id}/`
    """
    queryset = ProductImage.objects.select_related('product')
    serializer_class = ProductImageSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        """
        Determines permissions based on the action.
        - Public access: `list`, `retrieve`
        - Authenticated & owner required: `create`, `update`, `delete`
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]

    @swagger_auto_schema(
        operation_summary="List all product images",
        operation_description="Retrieves a list of all product images.",
        responses={200: ProductImageSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        """ List all product images """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a product image",
        operation_description="Gets details of a specific product image by its ID.",
        responses={
            200: ProductImageSerializer(),
            404: openapi.Response("Image not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """ Retrieve a single product image """
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Upload a product image",
        operation_description="Allows authenticated users to upload an image for their product. "
                              "The user must own the product.",
        request_body=ProductImageSerializer,
        responses={
            201: ProductImageSerializer(),
            400: openapi.Response("Invalid data"),
            403: openapi.Response("Permission denied")
        }
    )
    def create(self, request, *args, **kwargs):
        """ Upload a product image """
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a product image",
        operation_description="Allows the owner of the product to delete an image.",
        responses={
            204: openapi.Response("Image deleted"),
            403: openapi.Response("Permission denied"),
            404: openapi.Response("Image not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """ Delete a product image """
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Perform the creation of a product image, ensuring the user owns the product.
        :param serializer: The ProductImageSerializer instance containing validated data
        :raises PermissionDenied: If the current user is not the owner of the product
        """

        product = serializer.validated_data.get('product')

        if isinstance(product, int):
            product = get_object_or_404(Product, pk=product)

        self.check_product_ownership(self.request, product)

        serializer.save()


class ProductDetailView(APIView):
    """
    Retrieve detailed information about a specific product, including:
    - Product details (ID, name, slug, price, stock quantity, availability).
    - A cart form schema to help frontend applications structure cart additions.

    Products are only retrieved if they are marked as available (`is_available=True`).

    **URL Parameters:**
    - `id` (integer): The unique ID of the product.
    - `slug` (string): The slugified name of the product.

    **Responses:**
    - `200 OK`: Returns product details along with a cart form schema.
    - `404 Not Found`: If the product does not exist or is unavailable.

    Example Request:
    ```
    GET /api/products/1/organic-apples/
    ```

    Example Response (`200 OK`):
    ```json
    {
      "product": {
        "product_id": 1,
        "name": "Organic Apples",
        "slug": "organic-apples",
        "price": "12.99",
        "stock_quantity": 50,
        "is_available": true
      },
      "cart_product_form": {
        "quantity": 1
      }
    }
    ```
    """
    def get(self, request, id, slug):
        """
        Retrieve product details along with a cart form schema.

        **Parameters:**
        - `id` (int): The product's unique identifier.
        - `slug` (str): The product's slug.

        **Returns:**
        - `200 OK`: Product details + cart form.
        - `404 Not Found`: If the product does not exist or is unavailable.
        """
        # Fetch the product, ensuring it is available
        product = get_object_or_404(Product, id=id, slug=slug, is_available=True)

        # Prepare product data for response
        product_data = {
            'product_id': product.id,
            'name': product.name,
            'slug': product.slug,
            'price': str(product.price),  # Convert DecimalField to string
            'stock_quantity': product.stock_quantity,
            'is_available': product.is_available
        }

        # Initialize cart form serializer for frontend integration
        cart_product_form = CartAddProductSerializer()

        return Response(
            {'product': product_data, 'cart_product_form': cart_product_form.data},
            status=status.HTTP_200_OK
        )

