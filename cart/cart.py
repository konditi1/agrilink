from decimal import Decimal, InvalidOperation
from django.conf import settings
from products.models import Product
import logging
import copy

logger = logging.getLogger(__name__)

class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        Parameters
        request (django.http.HttpRequest): the request that contains the session

        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = self._validate_cart(cart)

    def _validate_cart(self, cart):
        """
        Ensure cart data is clean and valid.
        """
        cleaned_cart = {}
        for product_id, item in cart.items():
            try:
                quantity = int(item.get('quantity', 0))
                price = Decimal(item.get('price'))
                if quantity < 0 or price < 0:
                    raise ValueError("Negative values are not allowed.")
                cleaned_cart[product_id] = {'quantity': quantity, 'price': str(price)}
            except (ValueError, InvalidOperation, TypeError) as e:
                logger.error(f"Invalid cart data for product {product_id}: {e}")
        return cleaned_cart

    def add(self, product, quantity=1, update_quantity=False):
        """
        Add a product to the cart or update its quantity.
        Parameters
        product (Product): The product to add or update.
        quantity (int, optional): The quantity of the product to add. Default is 1.
        update_quantity (bool, optional): If True, update the quantity of the product. Default is False.
        Returns
        None
        """
        product_id = str(product.id)

        try:
            price = Decimal(product.price)
            if price <= 0:
                raise ValueError("Product price must be greater than zero.")
        except (InvalidOperation, TypeError, ValueError) as e:
            logger.error(f"Invalid price for product {product_id}: {e}")
            raise

        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(price)}

        if update_quantity:
            self.cart[product_id]['quantity'] = max(0, quantity)
        else:
            self.cart[product_id]['quantity'] = max(0, self.cart[product_id]['quantity'] + quantity)

        self.save()

    def save(self):
        """
        Mark the session as modified to ensure it is saved.
        This method should be called after any changes to the cart
        to ensure the session is updated with the latest cart state.
        """
        for item in self.cart.values():
            item['price'] = str(item['price'])
            item.pop('total_price', None)
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, product):
        """
        Remove a product from the cart.
        Parameters
        product (Product): The product to remove.
        Returns
        None
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products from the database.
        Yields:
            dict: A dictionary containing the product, quantity, and computed prices.
        """
        product_ids = self.cart.keys()
        
        # Fetch product objects and store them in a dictionary for faster lookup
        products = {str(product.id): product for product in Product.objects.filter(id__in=product_ids)}
        
        # Work on a copy to avoid modifying self.cart directly
        cart_copy = copy.deepcopy(self.cart)

        for product_id, item in cart_copy.items():
            item['product'] = products.get(product_id)
            
            try:
                item['price'] = Decimal(item['price'])
                if item['price'] <= 0:
                    raise ValueError(f"Negative or zero price for product {product_id}: {item['price']}")
                
                item['quantity'] = int(item['quantity'])
                if item['quantity'] <= 0:
                    raise ValueError(f"Invalid quantity for product {product_id}: {item['quantity']}")

                item['total_price'] = item['price'] * item['quantity']

            except (InvalidOperation, TypeError, ValueError) as e:
                logger.error(f"Cart data error for product {product_id}: {e}")
                item['total_price'] = Decimal('0.00')

            yield item

    def __len__(self):
        """
        Return the total number of items in the cart.
        Returns
        int: The total number of items in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())
    
    def get_total_price(self):
        """
        Return the total price of all items in the cart.
        Returns
        Decimal: The total price of all items in the cart.
        """
        return sum(Decimal(item['price']) * item['quantity']
                   for item in self.cart.values())
    
    def clear(self):
        """
        Clear the cart by removing all items safely.
        """
        if settings.CART_SESSION_ID in self.session:
            self.session[settings.CART_SESSION_ID] = {}  # Reset cart instead of deleting
            self.session.modified = True  # Ensure Django saves session changes

