import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        # Ensure superuser has a role (defaulting to 'farmer')
        if 'role' not in extra_fields:
            extra_fields['role'] = 'farmer'

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)  # UUID instead of integer ID
    username = None  # Remove username

    ROLE_CHOICES = [
        ('farmer', 'Farmer'),
        ('consumer', 'Consumer'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='consumer')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # Only email and password are required

    def __str__(self):
        return f"{self.email} ({self.role})"

class FarmerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True, related_name='farmer_profile')
    farm_name = models.CharField(max_length=100, blank=True, null=True)
    farm_location = models.CharField(max_length=100, blank=True, null=True)
    farm_size = models.CharField(max_length=100, blank=True, null=True)
    products = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.farm_name if self.farm_name else f"Farmer Profile ({self.user.email})"

class ConsumerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True, related_name='consumer_profile')
    preferred_products = models.TextField(blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Consumer Profile ({self.user.email})"
