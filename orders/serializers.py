from rest_framework import serializers
from .models import Order

class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving order details.
    """
    user_email = serializers.ReadOnlyField(source='user.email')
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'user_email', 'created_at', 'updated_at', 'is_paid', 'total_price', 'status']

