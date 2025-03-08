from rest_framework import generics, permissions
from .serializers import OrderSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from cart.cart import Cart
from .models import OrderItem, Order
from .serializers import OrderSerializer
from rest_framework.permissions import IsAuthenticated

class OrderCreateAPIView(APIView):
    """
    API endpoint to create an order from the cart.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handles order creation from the cart for the authenticated user.

        ### Workflow:
        1. **Check if the cart is not empty** – prevents ordering without items.
        2. **Validate request data** – uses `OrderCreateSerializer` for validation.
        3. **Create order & order items** – generates `Order` and `OrderItem` instances.
        4. **Clear the cart** – ensures cart is empty after order creation.
        5. **Return response** – returns order ID on success.

        ### Responses:
        - ✅ **201 Created** – Order successfully created, returns `{ "order_id": <UUID> }`
        - ❌ **400 Bad Request** – Invalid data or empty cart.
        """


        cart = Cart(request)

        if not cart:
            return Response({"error": "Cart is empty. Cannot place an order."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            order = serializer.save()

            # Create order items from the cart
            order_items = [
                OrderItem(order=order, product=item['product'], price=item['price'], quantity=item['quantity'])
                for item in cart
            ]
            OrderItem.objects.bulk_create(order_items)

            # Clear the cart after order creation
            cart.clear()

            return Response(
                {"message": "Order created successfully", "order_id": order.id},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserOrderListAPIView(generics.ListAPIView):
    """
    Retrieves a list of orders for the authenticated user.

    ### Endpoint:
    - **GET** `/accounts/api/orders/`

    ### Permissions:
    - 🔒 **Authentication required** (User must be logged in)

    ### Response:
    - ✅ **200 OK**: Returns a list of orders belonging to the authenticated user.
    - ❌ **401 Unauthorized**: If the user is not authenticated.

    ### Example Response:
    ```json
    [
        {
            "id": "b4d5f2a6-8c23-4f6c-a9b3-e5e5c729ad3b",
            "user": "a8aacd39-fb86-4bee-9009-a24a361a17da",
            "status": "pending",
            "total_price": "3500.00",
            "created_at": "2024-03-06T12:34:56Z",
            "order_items": [
                {
                    "product": "Tomatoes",
                    "quantity": 10,
                    "price": "500.00"
                }
            ]
        }
    ]
    ```
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')
