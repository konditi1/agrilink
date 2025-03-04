from rest_framework import serializers
from .models import Category, Product, ProductImage

class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False
    )
    children = serializers.SerializerMethodField()  # Optional: Load only if needed

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'children']
        read_only_fields = ['id', 'slug']

    def get_children(self, obj):
        """Return child categories only if 'include_children' is in the request."""
        request = self.context.get('request')
        if request and request.query_params.get('include_children') == 'true':
            children = obj.children.all()
            return CategorySerializer(children, many=True).data  # Recursively serialize children
        return None  # Default: Don't load children


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'is_primary', 'alt_text']
        read_only_fields = ['id']  # ID should be read-only

class ProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    seller_email = serializers.EmailField(source="seller.email", read_only=True)
    category = serializers.StringRelatedField()
    farm_name = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "seller", "seller_email", "farm_name", "category",
            "name", "slug", "description", "price", "unit", "stock_quantity",
            "is_organic", "is_available", "created_at", "updated_at",
            "primary_image", "images"
        ]
        read_only_fields = [
            "id", "slug", "created_at", "updated_at", 
            "seller_email", "farm_name", "primary_image"
        ]

    def get_images(self, obj):
        """Returns images in a hybrid manner (IDs by default, full data if requested)."""
        request = self.context.get("request")
        images = obj.images.all()

        if request and request.query_params.get("include_images") == "full":
            return ProductImageSerializer(images, many=True).data
        return [image.id for image in images]

    def get_farm_name(self, obj):
        """If seller is a farmer, return farm name from FarmerProfile, otherwise return None."""
        return getattr(obj.seller.farmer_profile, "farm_name", None)

    def get_primary_image(self, obj):
        """Returns the URL of the primary image, or None if no image exists."""
        primary_image = obj.images.filter(is_primary=True).only("image").first()
        return primary_image.image.url if primary_image else None


class ProductCreateSerializer(serializers.ModelSerializer):
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False),
        write_only=True, required=False
    )
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "category", "name", "description", "price", "unit",
            "stock_quantity", "is_organic", "is_available",
            "uploaded_images", "primary_image"
        ]
        read_only_fields = ["primary_image"]

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])

        # Assign seller from authenticated user
        validated_data["seller"] = self.context["request"].user

        # Create the product
        product = Product.objects.create(**validated_data)

        # Save images and determine primary image
        if uploaded_images:
            ProductImage.objects.bulk_create([
                ProductImage(product=product, image=image, is_primary=(i == 0))
                for i, image in enumerate(uploaded_images)
            ])

        return product

    def get_primary_image(self, obj):
        """Returns the URL of the primary image, or None if no image exists."""
        primary_image = obj.images.filter(is_primary=True).only("image").first()
        return primary_image.image.url if primary_image else None
