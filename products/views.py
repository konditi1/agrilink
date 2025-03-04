from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from django.db import transaction
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
    


from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, ProductImage
from .serializers import ProductSerializer, ProductCreateSerializer, ProductImageSerializer
from .permissions import IsOwnerOrReadOnly
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Q

from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products.
    """
    queryset = Product.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name', 'description', 'seller__username', 'category__name']
    filterset_fields = ['category', 'is_organic', 'is_available', 'seller', 'unit']
    ordering_fields = ['price', 'created_at', 'name', 'stock_quantity']
    ordering = ['-created_at']
    lookup_field = 'slug'

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return ProductSerializer


    def get_queryset(self):
        """Optimize queryset filtering using Q objects."""
        queryset = Product.objects.all()

        filters = Q()
        
        # Price range filtering
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price and max_price:
            filters &= Q(price__range=(min_price, max_price))
        elif min_price:
            filters &= Q(price__gte=min_price)
        elif max_price:
            filters &= Q(price__lte=max_price)

        # Seller filter
        seller_id = self.request.query_params.get('seller')
        if seller_id:
            filters &= Q(seller_id=seller_id)
        
          # Filter by farm name (if seller has a farmer profile)  
        farm_name = self.request.query_params.get('farm_name')
        if farm_name:
            filters &= Q(seller__farmer_profile__farm_name__icontains=farm_name)


        # Stock availability
        if self.request.query_params.get('in_stock') == 'true':
            filters &= Q(stock_quantity__gt=0)

        # Show only available products unless `show_all=true`
        if self.request.query_params.get('show_all') != 'true':
            filters &= Q(is_available=True)

        return queryset.filter(filters)


    @action(detail=False, methods=['get'])
    def my_products(self, request):
        """List all products owned by the current user."""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        products = Product.objects.filter(seller=request.user).select_related('seller')
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

 

    @action(detail=True, methods=['post'])
    def upload_images(self, request, slug=None):
        """Upload multiple images to a product efficiently using bulk_create with image resizing."""
        product = self.get_object()

        # Ownership check
        if product.seller != request.user:
            return Response({"detail": "You do not have permission to add images to this product."}, 
                            status=status.HTTP_403_FORBIDDEN)

        # Check if files were provided
        if 'images' not in request.FILES:
            return Response({"detail": "No images provided."}, status=status.HTTP_400_BAD_REQUEST)

        images = request.FILES.getlist('images')
        set_primary = request.data.get('set_primary', 'false').lower() == 'true'
        
        bulk_images = []
            # Load settings
        max_size = settings.PRODUCT_IMAGE_MAX_DIMENSIONS
        allowed_formats = settings.PRODUCT_IMAGE_ALLOWED_FORMATS

        def process_image(image_file):
            """Resize image while maintaining aspect ratio."""
            img = Image.open(image_file)
            
            # Ensure image is in a valid format
            if image_file.content_type not in allowed_formats:
                raise ValueError(f"Invalid file format: {image_file.content_type}. Only JPEG/PNG allowed.")
            
            # Convert mode if needed
            if img.mode in ("RGBA", "P"): 
                img = img.convert("RGB")

            # Resize image
            img.thumbnail(max_size, Image.ANTIALIAS)

            # Generate unique filename
            

            # Save to memory
            img_io = BytesIO()
            img_format = "JPEG" if image_file.content_type == "image/jpeg" else "PNG"
            img.save(img_io, format=img_format, quality=85)  # Adjust quality to reduce size
            
            # Create a new InMemoryUploadedFile
            return InMemoryUploadedFile(
                img_io, None, image_file.name, image_file.content_type, img_io.tell, None
            )

        # Process images
        for i, image_file in enumerate(images):
            try:
                resized_image = process_image(image_file)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            is_primary = (set_primary and i == 0) or (product.images.count() == 0 and i == 0)
            alt_text = request.data.get(f'alt_text_{i}', f'Image {i+1} for {product.name}')
            
            bulk_images.append(ProductImage(product=product, image=resized_image, is_primary=is_primary, alt_text=alt_text))

        # Bulk insert all images in a single query
        created_images = ProductImage.objects.bulk_create(bulk_images)

        # If primary image was changed, update existing images
        with transaction.atomic():
            if set_primary and bulk_images:
                product.images.filter(is_primary=True).exclude(id__in=[img.id for img in created_images]).update(is_primary=False)

        serializer = ProductImageSerializer(created_images, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['post'])
    def set_primary_image(self, request, slug=None):
        """Set a specific image as the primary image for a product."""
        product = self.get_object()

        # Ownership check
        if product.seller != request.user:
            return Response({"detail": "You do not have permission to modify this product."}, 
                            status=status.HTTP_403_FORBIDDEN)

        image_id = request.data.get('image_id')
        if not image_id:
            return Response({"detail": "No image ID provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product.images.filter(is_primary=True).update(is_primary=False)
            image = product.images.get(id=image_id)
            image.is_primary = True
            image.save()
            return Response({"success": True, "detail": f"Image {image_id} set as primary for {product.name}"})
        except ProductImage.DoesNotExist:
            return Response({"detail": f"Image with ID {image_id} not found for this product."}, 
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'])
    def delete_image(self, request, slug=None):
        """Delete a specific image from a product."""
        product = self.get_object()

        # Ownership check
        if product.seller != request.user:
            return Response({"detail": "You do not have permission to modify this product."}, 
                            status=status.HTTP_403_FORBIDDEN)

        image_id = request.data.get('image_id')
        if not image_id:
            return Response({"detail": "No image ID provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            image = product.images.get(id=image_id)
            was_primary = image.is_primary
            image.delete()

            # If the primary image was deleted, set a new one if available
            if was_primary:
                new_primary = product.images.filter(is_primary=False).first()
                if new_primary:
                    new_primary.is_primary = True
                    new_primary.save()

            return Response({"success": True, "detail": f"Image {image_id} deleted from {product.name}"})
        except ProductImage.DoesNotExist:
            return Response({"detail": f"Image with ID {image_id} not found for this product."}, 
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get a selection of featured products."""
        featured = Product.objects.filter(is_available=True, stock_quantity__gt=0).order_by('-created_at')[:8]
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def organic(self, request):
        """Get organic products."""
        organic = Product.objects.filter(is_available=True, is_organic=True, stock_quantity__gt=0)
        page = self.paginate_queryset(organic)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(organic, many=True)
        return Response(serializer.data)


