from django.contrib.auth.password_validation import validate_password
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import CustomUser
from .serializers import UserRegisterSerializer, CustomUserSerializer, FarmerProfileSerializer, ConsumerProfileSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings

class UserRegistrationAPIView(CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # User is created, signals handle profile creation
            
            return Response({
                "user": CustomUserSerializer(user).data,  # Format user data for response
                "message": "User registered successfully",
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class FarmerProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = FarmerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if not hasattr(self.request.user, 'farmer_profile'):
            return Response({"detail": "Farmer profile not found"}, status=status.HTTP_404_NOT_FOUND)
        return self.request.user.farmer_profile
    

class ConsumerProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = ConsumerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if not hasattr(self.request.user, 'consumer_profile'):
            return Response({"detail": "Consumer profile not found"}, status=status.HTTP_404_NOT_FOUND)
        return self.request.user.consumer_profile


@api_view(['POST'])
@permission_classes([AllowAny])
def check_username_email(request):
    username = request.data.get('username', '')
    email = request.data.get('email', '')
    
    response = {
        'username_exists': CustomUser.objects.filter(username=username).exists() if username else False,
        'email_exists': CustomUser.objects.filter(email=email).exists() if email else False
    }
    
    return Response(response)


class PassWordResetAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"detail": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            send_mail(
                'Reset your password',
                f'Click the link below to reset your password: {reset_link}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )

            return Response({"detail": "Password reset email has been sent"}, status=status.HTTP_200_OK)
        
        except CustomUser.DoesNotExist:
            # for security reasons, we still return a positive response
            return Response({"detail": "User does not exist"}, status=status.HTTP_200_OK)
        

class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')

        if not all([uid, token, password]):
            return Response({"detail": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({"detail": "Invalid link or user does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            validate_password(password, user)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()
        return Response({"detail": "Password has been reset successfully"}, status=status.HTTP_200_OK)