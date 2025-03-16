from django.contrib.auth.password_validation import validate_password
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import CustomUser
from agrilink.tasks import send_email
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import UserRegisterSerializer, CustomUserSerializer, FarmerProfileSerializer, ConsumerProfileSerializer, PasswordResetSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import ValidationError
from django.conf import settings
from rest_framework.permissions import BasePermission


class IsConsumer(BasePermission):
    """
    Custom permission to allow only users with a consumer profile to access ConsumerProfileAPIView.
    """

    def has_permission(self, request, view):
        # Allow if user is authenticated and has a consumer profile
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, 'consumer_profile'))

    def has_object_permission(self, request, view, obj):
        # Ensure the user can only access their own consumer profile
        return obj.user == request.user


class IsFarmer(BasePermission):
    """
    Custom permission to allow only farmers to access FarmerProfileAPIView.
    """

    def has_permission(self, request, view):
        # Ensure the user is authenticated and has a farmer profile
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, 'farmer_profile'))

    def has_object_permission(self, request, view, obj):
        # Ensure the user is the owner of the farmer profile they are accessing
        return obj.user == request.user


@api_view(['GET'])
def api_documentation(request):
    """
    # Authentication
    
    This API uses JWT Authentication. To authenticate:
    
    1. Obtain tokens by sending credentials to `/accounts/api/token/`
    2. Include the access token in the Authorization header as: `Bearer <token>`
    3. Refresh tokens using `/accounts/api/token/refresh/`
    4. Logout by sending the refresh token to `/accounts/api/logout/`
    
    More details can be found in the Swagger documentation.
    """
    return Response({"message": "See documentation at /swagger/"})

class UserRegistrationAPIView(CreateAPIView):
    """
    Register a new user.
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description="""
        Creates a new user account and returns the user data along with a success message.

        **Request Body:**
        - **email** (string, required): User's email address
        - **role** (string, required): `"farmer"` or `"consumer"`
        - **password** (string, required): User's password (must meet validation criteria)
        - **confirm_password** (string, required): Must match `password`
        - **first_name** (string, required): User's first name
        - **last_name** (string, required): User's last name
        - **phone** (string, optional): Must be in international format (e.g., `+254712345678`)
        - **profile_picture** (file, optional): Profile picture upload

        **Responses:**
        - ✅ **201 Created**: User registered successfully
        - ❌ **400 Bad Request**: Validation errors
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "role", "password", "confirm_password", "first_name", "last_name"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, example="user@example.com"),
                "role": openapi.Schema(type=openapi.TYPE_STRING, enum=["farmer", "consumer"], example="farmer"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="SecurePassword123!"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", example="SecurePassword123!"),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, example="John"),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING, example="Doe"),
                "phone": openapi.Schema(type=openapi.TYPE_STRING, example="+254712345678"),
                "profile_picture": openapi.Schema(type=openapi.TYPE_FILE, description="Optional profile picture"),
            },
        ),
        responses={
            201: openapi.Response(
                description="User registered successfully",
                schema=CustomUserSerializer
            ),
            400: openapi.Response(
                description="Bad Request - Validation errors"
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # User is created, signals handle profile creation
            
            return Response({
                "user": CustomUserSerializer(user).data,  # Format user data for response
                "message": "User registered successfully",
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserProfileAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Retrieve the authenticated user's profile",
        operation_description="""
            This endpoint allows an authenticated user to retrieve their profile information.

            **Permissions:**  
            - Only authenticated users can access this endpoint.  

            **Responses:**  
            - `200 OK` - Returns the user's profile data.  
            - `403 Forbidden` - If the user is not authenticated.  
        """,
        responses={
            200: openapi.Response(
                description="User profile retrieved successfully",
                schema=CustomUserSerializer()
            ),
            403: openapi.Response(
                description="Forbidden - User is not authenticated"
            ),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update the authenticated user's profile",
        operation_description="""
            Allows an authenticated user to update their profile information.

            **Permissions:**  
            - Only authenticated users can access this endpoint.  

            **Request Body:**  
            - `first_name` (string, optional): User's first name  
            - `last_name` (string, optional): User's last name  
            - `phone` (string, optional): User's phone number  
            - `profile_picture` (file, optional): Profile picture  

            **Responses:**  
            - `200 OK` - User profile updated successfully  
            - `400 Bad Request` - Invalid input data  
            - `403 Forbidden` - If the user is not authenticated  
        """,
        request_body=CustomUserSerializer,
        responses={
            200: openapi.Response(
                description="User profile updated successfully",
                schema=CustomUserSerializer()
            ),
            400: openapi.Response(
                description="Bad Request - Invalid input data"
            ),
            403: openapi.Response(
                description="Forbidden - User is not authenticated"
            ),
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary="Partially update the authenticated user's profile",
        operation_description="""
            Allows an authenticated user to partially update their profile.

            **Permissions:**  
            - Only authenticated users can access this endpoint.  

            **Request Body:**  
            - Any subset of user profile fields can be updated.  

            **Responses:**  
            - `200 OK` - User profile updated successfully  
            - `400 Bad Request` - Invalid input data  
            - `403 Forbidden` - If the user is not authenticated  
        """,
        request_body=CustomUserSerializer,
        responses={
            200: openapi.Response(
                description="User profile partially updated successfully",
                schema=CustomUserSerializer()
            ),
            400: openapi.Response(
                description="Bad Request - Invalid input data"
            ),
            403: openapi.Response(
                description="Forbidden - User is not authenticated"
            ),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete the authenticated user's profile",
        operation_description="""
            Allows an authenticated user to delete their profile.

            **Permissions:**  
            - Only authenticated users can access this endpoint.  

            **Responses:**  
            - `204 No Content` - User profile deleted successfully  
            - `403 Forbidden` - If the user is not authenticated  
        """,
        responses={
            204: openapi.Response(
                description="User profile deleted successfully"
            ),
            403: openapi.Response(
                description="Forbidden - User is not authenticated"
            ),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_object(self):
        """
        Retrieve the current authenticated user.
        """

        return self.request.user


class FarmerProfileAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve or update the authenticated user's farmer profile.

    **Permissions:**
    - Authenticated users only

    **Response:**
    - 200 OK: Returns the farmer profile
    - 404 Not Found: If user does not have a farmer profile
    """
    serializer_class = FarmerProfileSerializer
    permission_classes = [IsAuthenticated, IsFarmer]

    def get_object(self):
        """
        Retrieve the farmer profile associated with the requesting user.

        If the user does not have a farmer profile, return a 404 response.
        """

        if not hasattr(self.request.user, 'farmer_profile'):
            return Response({"detail": "Farmer profile not found"}, status=status.HTTP_404_NOT_FOUND)
        return self.request.user.farmer_profile
    

class ConsumerProfileAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete the authenticated user's consumer profile.

    **Permissions:**
    - `IsAuthenticated`: User must be logged in.
    - `IsConsumer`: User must have a consumer profile.
    """
   
    serializer_class = ConsumerProfileSerializer
    permission_classes = [IsAuthenticated, IsConsumer]

    def get_object(self):
        """
        Return the consumer profile associated with the requesting user.

        If the user has no consumer profile, return a 404 response.
        """
        if not hasattr(self.request.user, 'consumer_profile'):
            return Response({"detail": "Consumer profile not found"}, status=status.HTTP_404_NOT_FOUND)
        return self.request.user.consumer_profile
    
@swagger_auto_schema(
    method='post',
    operation_summary="Check Email Availability",
    operation_description="""
    Checks if a given email is already registered.

    **Permissions:**  
    - `AllowAny`: Accessible to both authenticated and unauthenticated users.

    **Request Body:**  
    - `email` (string, optional): Email to check for availability.  

    **Responses:**  
    - `200 OK`: Returns the availability status for email.  
    - `400 Bad Request`: If request data is invalid.
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, example="john@example.com"),
        },
    ),
    responses={
        200: openapi.Response(
            description="Availability check result",
            examples={
                "application/json": {
                    "email_exists": True
                }
            }
        ),
        400: openapi.Response(
            description="Invalid request data",
            examples={
                "application/json": {
                    "detail": "Invalid request data."
                }
            }
        ),
    },
)
@api_view(['POST'])
@permission_classes([AllowAny])
def check_email(request):
    """
    Check if an email already exist in the database.
    """
    email = request.data.get('email', '')
    
    response = {
        'email_exists': CustomUser.objects.filter(email=email).exists() if email else False
    }
    
    return Response(response)



class LogoutAPIView(APIView):
    """
    Log out the user by blacklisting the provided refresh token.

    **Request Data:**
    - `refresh` (string): The refresh token to blacklist

    **Response:**
    - 200 OK: Successfully logged out
    - 400 Bad Request: If token is invalid
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Blacklists the refresh token provided in the request body.

        :param request: Request object containing the refresh token to be blacklisted
        :return: Response indicating success or failure of the logout operation
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
           
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PassWordResetAPIView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        operation_summary="Request Password Reset",
        operation_description="Sends a password reset link to the provided email if it exists in the system.",
        request_body=PasswordResetSerializer,
        responses={
            200: openapi.Response(
                description="Password reset email sent",
                examples={
                    "application/json": {
                        "detail": "Password reset email has been sent"
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid request",
                examples={
                    "application/json": {
                        "email": ["This field is required."]
                    }
                }
            ),
        },
    )

    def post(self, request):
               
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        
        try:
            user = CustomUser.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.FRONTEND_URL}accounts/api/password-reset/confirm/{uid}/{token}/"


            subject = "Reset your password"
            body = f"Click the link below to reset your password: {reset_link}"
            
            send_email.delay(email, subject, body)

            return Response({"detail": "Password reset email has been sent"}, status=status.HTTP_200_OK)
        
        except CustomUser.DoesNotExist:
            # Return success response to prevent email enumeration
            return Response(
                {"detail": "If a user with that email exists, a password reset email has been sent."},
                status=status.HTTP_200_OK,
            )

class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uid, token):
        """
        Handles password reset confirmation.

        Accepts the user's UID, token, and new password from the request data.
        Validates the presence of all fields and checks the validity of the 
        token and user. Validates the password using Django's password 
        validation utilities. If all checks pass, updates the user's password 
        with the new password. Returns a success response if the password is 
        reset successfully, or an error response if any validation fails.

        :param request: Request object containing the UID, token, and new password
        :return: Response indicating success or failure of the password reset operation
        """

        password = request.data.get('password')

        if not password:
            return Response({"detail": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        
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