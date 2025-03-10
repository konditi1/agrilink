from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, FarmerProfile, ConsumerProfile
from products.serializers import ProductSerializer
from rest_framework import serializers
import re

class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = ['farm_name', 'farm_location', 'farm_size', 'products']
        read_only_fields = ['user']


def validate_phone(value):
    """
    Validate a phone number. Allows empty values but enforces correct format if provided.
    """
    if value and not re.match(r'^\+\d{10,15}$', value):  
        raise serializers.ValidationError("Phone number must be in international format (e.g., +254712345678).")
    return value


class ConsumerProfileSerializer(serializers.ModelSerializer):
    preferred_products = serializers.SerializerMethodField()  # Use method to safely retrieve products

    class Meta:
        model = ConsumerProfile
        fields = ['preferred_products', 'delivery_address']
        read_only_fields = ['user']

    def get_preferred_products(self, obj):
        """
        Safely get the list of preferred products.
        Returns an empty list if no products are linked.
        """
        if hasattr(obj, 'preferred_products'):
            products = obj.preferred_products.all()
            return ProductSerializer(products, many=True).data
        return []

class CustomUserSerializer(serializers.ModelSerializer):
    farmer_profile = serializers.SerializerMethodField()
    consumer_profile = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(required=False, allow_null=True)  # Optional
    email = serializers.EmailField(read_only=True)
    phone = serializers.CharField(validators=[validate_phone])
    password = serializers.CharField(write_only=True, required=False)  # Optional password update
    confirm_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 
                  'role', 'phone', 'profile_picture', 'password', 'confirm_password',
                  'farmer_profile', 'consumer_profile']
        read_only_fields = ['id', 'email']

    def get_farmer_profile(self, obj):
        if obj.role == 'farmer' and hasattr(obj, 'farmer_profile'):
            return FarmerProfileSerializer(obj.farmer_profile).data
        return None

    def get_consumer_profile(self, obj):
        if obj.role == 'consumer' and hasattr(obj, 'consumer_profile'):
            return ConsumerProfileSerializer(obj.consumer_profile).data
        return None

    def validate(self, data):
        """
        Ensure passwords match if provided.
        """
        password = data.get('password')
        confirm_password = data.get('confirm_password')

        if password or confirm_password:  # Only validate if either field is provided
            if password != confirm_password:
                raise serializers.ValidationError({"password": "Passwords do not match."})
            validate_password(password)  # Enforce strong password rules

        return data

    def update(self, instance, validated_data):
        """
        Update user fields and handle password updates correctly.
        """
        password = validated_data.pop('password', None)
        validated_data.pop('confirm_password', None)  # Remove safely

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)  # Securely hash and update password

        instance.save()
        return instance




class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    phone = serializers.CharField(validators=[validate_phone])  # Apply phone validation

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role', 'first_name', 'last_name', 'phone', 'profile_picture', 'password', 'confirm_password']
        read_only_fields = ['id']
    def validate(self, data):
        """
        Validate that the password and confirm_password match.

        Args:
            data (dict): The data to validate.

        Returns:
            dict: The validated data.

        Raises:
            serializers.ValidationError: If the passwords do not match.
        """
        confirm_password = data.get('confirm_password')  # Store separately instead of removing
        if data['password'] != confirm_password:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        """
        Create a new user with the given validated data.

        Args:
            validated_data (dict): The validated data to use when creating the user.

        Returns:
            CustomUser: The newly created user.

        Note:
            The `role` field is explicitly stored on the user model for use by
            the signals that handle the creation of the farmer/consumer profile.
        """
        validated_data.pop('confirm_password', None)
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role'],  # Store role for signals to use
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''), 
            phone=validated_data.get('phone', ''),
            profile_picture=validated_data.get('profile_picture', None)
        )
        return user


