from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .cart import Cart
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import CartAddProductSerializer
from products.models import Product
from rest_framework.exceptions import ValidationError

class CartAddProductView(APIView):
    """
    Add a product to the cart or update its quantity.

    ### Endpoint:
    - **POST** `/cart/add/<product_id>/`

    ### Request Body:
    - **quantity** (*integer*, required): Number of items to add.
    - **override** (*boolean*, required): If `true`, replaces the quantity in the cart. If `false`, adds to the existing quantity.

    ### Responses:
    - ✅ **200 OK**: Product successfully added.
    - ❌ **400 Bad Request**: Validation error (e.g., exceeding stock).
    - ❌ **404 Not Found**: Product does not exist.

    ### Example Request:
    ```json
    {
        "quantity": 2,
        "override": true
    }
    ```

    ### Example Response:
    ```json
    {
        "detail": "Product added to cart successfully.",
        "product_id": 1,
        "product_name": "Organic Tomatoes",
        "quantity": 2,
        "available_stock": 50
    }
    ```
    """

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of items to add"),
                'override': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Replace quantity (true) or add more (false)"),
            },
            required=['quantity', 'override']
        ),
        responses={
            200: openapi.Response('Product added to cart successfully'),
            400: openapi.Response('Bad request'),
            404: openapi.Response('Product not found')
        }
    )
    
    def post(self, request, product_id):
        cart = Cart(request)
        self.product = get_object_or_404(Product, id=product_id)
        
        serializer = CartAddProductSerializer(
            data=request.data,
            context={'product': self.product}
        )

        if serializer.is_valid():
            data = serializer.validated_data
            quantity = data['quantity']
            override = data['override']

            current_quantity = cart.cart.get(str(self.product.id), {}).get('quantity', 0)
            new_quantity = quantity if override else current_quantity + quantity

            if new_quantity > self.product.stock_quantity:
                return Response(
                    {'detail': 'Cannot add more than available stock.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart.add(product=self.product, quantity=quantity, update_quantity=override)
            return Response(
                {
                    'detail': 'Product added to cart successfully.',
                    'product_id': self.product.id,
                    'product_name': self.product.name,
                    'quantity': new_quantity,
                    'available_stock': self.product.stock_quantity
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartRemoveProductView(APIView):
    """
    Remove a product from the cart.

    ### Endpoint:
    - **POST** `/cart/remove/<product_id>/`

    ### Responses:
    - ✅ **200 OK**: Product successfully removed.
    - ❌ **404 Not Found**: Product not in cart.

    ### Example Response:
    ```json
    {
        "detail": "Product removed from cart successfully.",
        "cart": [
            {
                "product_id": 2,
                "product_name": "Fresh Lettuce",
                "quantity": 1,
                "price": "150.00",
                "total_price": "150.00"
            }
        ],
        "total_price": "150.00"
    }
    ```
    """

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Product removed from cart successfully'),
            404: openapi.Response('Product not found in cart')
        }
    )
    def post(self, request, product_id):

        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)

        # Check if the product is in the cart
        if str(product.id) not in cart.cart:
            return Response(
                {'detail': 'Product not found in cart.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Remove product from cart
        cart.remove(product)

        # Prepare updated cart details
        cart_data = [
            {
                'product_id': item['product'].id,
                'product_name': item['product'].name,
                'quantity': item['quantity'],
                'price': str(item['price']),
                'total_price': str(item['total_price']),
            }
            for item in cart
        ]

        return Response(
            {
                'detail': 'Product removed from cart successfully.',
                'cart': cart_data,
                'total_price': str(cart.get_total_price()),
            },
            status=status.HTTP_200_OK
        )
    

class CartDetailView(APIView):
    """
    Retrieve the current cart details.

    ### Endpoint:
    - **GET** `/cart/`

    ### Responses:
    - ✅ **200 OK**: Returns the list of items in the cart.

    ### Example Response:
    ```json
    {
        "cart": [
            {
                "product_id": 1,
                "product_name": "Organic Tomatoes",
                "quantity": 2,
                "price": "500.00",
                "total_price": "1000.00"
            }
        ],
        "total_price": "1000.00"
    }
    ```
    """

    @swagger_auto_schema(
        responses={
            200: openapi.Response('Returns cart details with total price')
        }
    )
    def get(self, request):
        cart = Cart(request)
        cart_data = [
            {
                'product_id': item['product'].id,
                'product_name': item['product'].name,
                'quantity': item['quantity'],
                'price': str(item['price']),
                'total_price': str(item['total_price']),
            }
            for item in cart
        ]

        return Response(
            {
                'cart': cart_data,
                'total_price': str(cart.get_total_price()),
            },
            status=status.HTTP_200_OK
        )