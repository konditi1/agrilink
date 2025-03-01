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
    """Ensure phone number is valid (e.g., +254712345678)"""
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
        """Ensure password and confirm_password match"""
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        """Create a new user and allow signals to handle profile creation."""
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role'],  # Store role for signals to use
            phone=validated_data.get('phone', ''),
            profile_picture=validated_data.get('profile_picture', None)
        )
        return user


