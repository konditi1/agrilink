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
    - Checks product stock before adding.
    - Ensures you cannot add more than available stock.
    """
    def get_serializer_context(self):
        """
        Returns a dictionary containing the product instance to be passed to the serializer context.
        """
        return {'product': self.product}
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of items to add"),
                'override': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Whether to override the current quantity"),
            },
            required=['quantity', 'override']
        ),
        responses={
            200: openapi.Response('Product added to cart successfully'),
            400: openapi.Response('Bad request')
        }
    )
    
    def post(self, request, product_id):
        cart = Cart(request)
        self.product = get_object_or_404(Product, id=product_id)
        
        serializer = CartAddProductSerializer(
            data=request.data,
            context=self.get_serializer_context()
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
    Remove a product from the cart and return the updated cart details.
    """
    def post(self, request, product_id):
        """
        Remove a product from the cart and return the updated cart details.        
        Args
            request (HttpRequest): The HTTP request object containing user data.
            product_id (int): The ID of the product to be removed from the cart.        
        Returns
            Response: A Response object containing a success message and the updated cart details.
            - If the product is not found in the cart, returns a 404 status with an error message.
            - If the product is successfully removed, returns a 200 status with the updated cart and total price.
        """

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
    Returns the list of products in the cart and the total price.
    """
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