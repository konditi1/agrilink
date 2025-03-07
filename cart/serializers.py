from rest_framework import serializers

class CartAddProductSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
        default=1,
        help_text="The number of items to add to the cart (minimum: 1)."
    )
    override = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Set to true to override the existing quantity in the cart. If false, the quantity will be added to the current total."
    )
    def validate_quantity(self, value):
        """
        Ensure the requested quantity does not exceed available stock.
        Adjusts max quantity dynamically based on the product type.
        """
        product = self.context.get("product")  # Product should be passed in context
        if not product:
            raise serializers.ValidationError("Product is required.")

        # Check if product is available
        if not product.is_available:
            raise serializers.ValidationError(f"Sorry, {product.name} is not available.")

        # Restrict quantity to available stock
        if value > product.stock_quantity:
            raise serializers.ValidationError(
                f"Only {product.stock_quantity} {product.get_unit_display()} available in stock."
            )

        return value
