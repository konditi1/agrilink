from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='children', on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        """
        Overwrite the save method to ensure the slug field is always filled.
        If the slug field is empty, it will be filled with the slugified name.
        If the slug field is not empty, it will be overwritten with the slugified
        version of the current slug.
        """
        if not self.slug:  
            self.slug = slugify(self.name)
        else:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']


class Product(models.Model):
    UNIT_CHOICES = [
    # Weight-based units
    ('kg', 'Kilograms'),
    ('g', 'Grams'),
    ('mg', 'Milligrams'),
    ('lb', 'Pounds'),
    ('oz', 'Ounces'),

    # Volume-based units
    ('l', 'Liters'),
    ('ml', 'Milliliters'),
    ('gal', 'Gallons'),
    ('pt', 'Pints'),
    ('qt', 'Quarts'),

    # Count-based units
    ('pcs', 'Pieces'),
    ('dozen', 'Dozen'),
    ('half_dozen', 'Half Dozen'),
    ('pair', 'Pair'),
    ('bundle', 'Bundle'),

    # Container-based units
    ('box', 'Box'),
    ('bag', 'Bag'),
    ('crate', 'Crate'),
    ('basket', 'Basket'),
    ('jar', 'Jar'),
    ('bottle', 'Bottle'),

    # Special units
    ('bunch', 'Bunch'),
    ('head', 'Head'),  # for lettuce, cabbage, etc.
    ('stick', 'Stick'), # for herbs, cinnamon sticks
    ('clove', 'Clove'),  # for garlic, etc.
    ('slice', 'Slice'),  # for cut produce
]
    
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey('Category', on_delete=models.PROTECT, related_name='products')  # Prevent accidental deletion
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, db_index=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    unit = models.CharField(
    max_length=15,
    choices=UNIT_CHOICES,
    verbose_name='Unit of Measurement',
    help_text='Select the unit used to measure the product (e.g., kilograms, liters, pieces).'
)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_organic = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["price"], name="idx_product_price"),
            models.Index(fields=["seller"], name="idx_product_seller"),
            models.Index(fields=["stock_quantity"], name="idx_product_stock"),
            models.Index(fields=["is_available"], name="idx_product_available"),
            models.Index(fields=["created_at"], name="idx_product_created"),
        ]
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """
        Overridden save method that assigns a slug if none is provided.
        
        If no slug is provided, it will be generated from the product's name.
        If the generated slug already exists, a counter will be appended to it
        until a unique slug is found.
        """
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            base_slug = self.slug
            counter = 1

            # Ensure slug uniqueness
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        Returns the name of the product as a string.
        
        This is a more human-readable representation of the product,
        useful for debugging and logging purposes.
        """
        return self.name
    

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', db_index=True)
    image = models.ImageField(upload_to='product_images/')
    is_primary = models.BooleanField(default=False)  # Ensures one main image
    alt_text = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        """
        Returns a string representation of the product image.
        
        This is a more human-readable representation of the product image,
        useful for debugging and logging purposes.
        """
        return f"Image for {self.product.name}"

