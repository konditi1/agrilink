from decimal import Decimal
import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from orders.models import Order
from .models import Payment

# Stripe setup
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    
    """
    Create a Stripe checkout session for the authenticated user's order.

    ### Request
    - **Method** POST
    - **Body** JSON object containing 'order_id' as a key.

    **Returns**
    - 201: Checkout session created successfully. Returns session ID and URL.
    - 400: Order has already been paid.
    - 500: Internal server error with details.
    """

    order_id = request.data.get('order_id')
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.paid:
        return Response({"detail": "This order has already been paid."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Construct checkout session data
        session_data = {
            'mode': 'payment',
            'client_reference_id': str(order.id),
            'success_url': request.build_absolute_uri(reverse('payment:payment_success')),
            'cancel_url': request.build_absolute_uri(reverse('payment:payment_cancel')),
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': int(order.total_price * 100),  # Convert Decimal to cents
                    'product_data': {
                        'name': f"Order {order.id}",
                    },
                },
                'quantity': 1,
            }],
        }

        # Create a Stripe checkout session
        session = stripe.checkout.Session.create(**session_data)

        # Store session info in the Payment model
        Payment.objects.create(
            user=request.user,
            order=order,
            stripe_checkout_id=session.id,
            amount=order.total_price
        )

        return Response({"session_id": session.id, "url": session.url}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def stripe_webhook(request):
    """
    Handle Stripe webhook events (for payment confirmation).
    """
    payload = request.body
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return Response({"detail": "Invalid payload or signature."}, status=status.HTTP_400_BAD_REQUEST)

    # Handle checkout session completion
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_successful_payment(session)

    return Response(status=status.HTTP_200_OK)


def handle_successful_payment(session):
    """
    Update order and payment status after successful Stripe payment.
    """
    try:
        payment = Payment.objects.get(stripe_checkout_id=session['id'])
        order = payment.order
        order.paid = True
        order.save()

        payment.status = 'completed'
        payment.save()

    except Payment.DoesNotExist:
        pass
