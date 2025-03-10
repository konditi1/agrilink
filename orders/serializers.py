from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for order items inside an order.
    """
    product = serializers.CharField(source='product.name')  # Show product name

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving order details.
    """
    user_email = serializers.ReadOnlyField(source='user.email')
    user = serializers.UUIDField(source='user.id', read_only=True)  # Return user ID
    order_items = OrderItemSerializer(many=True, read_only=True, source='items')
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'user_email', 'status', 'total_price',  'created_at', 'updated_at', 'is_paid', 'order_items']

    def create(self, validated_data):
        """
        Assigns the authenticated user automatically before saving.
        """
        validated_data['user'] = self.context['request'].user  # Auto-assign user
        return super().create(validated_data)
