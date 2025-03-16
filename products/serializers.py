from rest_framework import serializers
from .utils import process_image
from .models import Category, Product, ProductImage

class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False
    )
    children = serializers.SerializerMethodField()  # Optional: Load only if needed

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'children', 'created_at',
                  'updated_at', 'is_approved', 'created_by']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'created_by']

    def get_children(self, obj):
        """
        Retrieves and serializes the children of a given category object if the request
        includes a query parameter 'include_children' set to 'true'. If the parameter is 
        not present or set to any other value, it returns an empty list by default.
        
        Args:
            obj: The category object for which children need to be retrieved.

        Returns:
            A list of serialized child category objects if 'include_children' is 'true',
            or an empty list otherwise.
        """

        request = self.context.get('request')
        if request and request.query_params.get('include_children') == 'true':
            children = obj.children.all()
            return CategorySerializer(children, many=True).data  # Recursively serialize children
        return []  # Default: Don't load children


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'is_primary', 'alt_text']
        read_only_fields = ['id']  # ID should be read-only
    
    def validate_image(self, value):
        """
        Validate and process the uploaded image.
        """
        try:
            return process_image(value)
        except ValueError as e:
            raise serializers.ValidationError({"image": str(e)})

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
        """
        Return a list of IDs of all images if 'include_images' is not provided,
        otherwise return a list of serialized ProductImage objects.
        """
        request = self.context.get("request")
        images = obj.images.all()

        if request and request.query_params.get("include_images") == "full":
            return ProductImageSerializer(images, many=True).data
        return list(images.values_list("id", flat=True))

    def get_farm_name(self, obj):
        """
        Retrieve the farm name associated with the seller's farmer profile.

        If the seller's farmer profile has a farm name, return it. Otherwise,
        return None.
        """

        return getattr(obj.seller.farmer_profile, "farm_name", None)

    def get_primary_image(self, obj):
        """
        Return the URL of the primary image if it exists, otherwise return None.
        
        Retrieves the primary image of the product and returns its URL if it exists,
        otherwise returns None.
        """
        primary_image = obj.images.filter(is_primary=True).first()
        return primary_image.image.url if primary_image else None


class ProductCreateSerializer(serializers.ModelSerializer):
    uploaded_images = serializers.ListSerializer(
        child=serializers.ImageField(allow_empty_file=False, required=False, write_only=True),
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
        """
        Create a new product with the given validated data.

        Pops the `uploaded_images` key from the validated data and uses it to
        create ProductImage objects after the product has been created. The
        first image in the list is made the primary image.

        The seller is assigned from the authenticated user in the request context.

        Returns the newly created Product object.
        """
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
        """
        Return the URL of the primary image if it exists, otherwise return None.
        
        Retrieves the primary image of the product and returns its URL if it exists,
        otherwise returns None.
        """
        primary_image = obj.images.filter(is_primary=True).only("image").first()
        return primary_image.image.url if primary_image else None
