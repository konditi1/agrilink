from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, FarmerProfile, ConsumerProfile
from rest_framework import serializers
import re

class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = '__all__'
        read_only_fields = ['user']

class ConsumerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsumerProfile
        fields = '__all__'
        read_only_fields = ['user']

class CustomUserSerializer(serializers.ModelSerializer):
    farmer_profile = FarmerProfileSerializer(read_only=True)
    consumer_profile = ConsumerProfileSerializer(read_only=True)
    profile_picture = serializers.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 
                'role', 'phone', 'profile_picture', 'farmer_profile', 'consumer_profile']
        read_only_fields = ['id']



def validate_phone(value):
    """
    Validate a phone number.
    
    Args:
        value (str): The phone number to validate.
    
    Returns:
        str: The validated phone number.
    
    Raises:
        serializers.ValidationError: If the phone number is not in international format.
    """
    if not re.match(r'^\+\d{10,15}$', value):  
        raise serializers.ValidationError("Phone number must be in international format (e.g., +254712345678).")
    return value

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    phone = serializers.CharField(validators=[validate_phone])  # Apply phone validation

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role', 'phone', 'profile_picture', 'password', 'confirm_password']

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
        if data['password'] != data.pop('confirm_password'):
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
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role'],  # Store role for signals to use
            phone=validated_data.get('phone', ''),
            profile_picture=validated_data.get('profile_picture', None)
        )
        return user


