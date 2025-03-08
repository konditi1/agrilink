# orders/models.py

import uuid
from django.db import models
from django.conf import settings
from products.models import Product

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_paid = models.BooleanField(default=False)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        default='pending'
    )

    def __str__(self):
        """
        Return a human-readable string representation of the order.

        Example:
            "Order 5c6f1f36-6f00-4e5e-9f5e-5f6f1f80 by example@example.com"
        """
        return f"Order {self.id} by {self.user.email}"

    def get_total_price(self):
        """
        Return the total price of all items in the order.

        Returns
        -------
        Decimal
            The total price of all items in the order.
        """
        return sum(item.get_total() for item in self.items.all())

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def get_total(self):
        """
        Return the total price of this order item.

        Returns
        -------
        Decimal
            The total price of this order item.
        """
        return self.quantity * self.price

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)

    def __str__(self):
        """
        Return a human-readable string representation of the payment.

        Example:
            "Payment for Order 5c6f1f36-6f00-4e5e-9f5e-5f6f1f80"
        """
        
        return f"Payment for Order {self.order.id}"
