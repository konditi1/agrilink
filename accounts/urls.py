from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path
from . import views


urlpatterns = [
    # JWT authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User registration and profile
    path('api/register/', views.UserRegistrationAPIView.as_view(), name='user-registration'),
    path('api/profile/', views.UserProfileAPIView.as_view(), name='user-profile'),
    path('api/farmer/', views.FarmerProfileAPIView.as_view(), name='farmer-profile'),
    path('api/consumer/', views.ConsumerProfileAPIView.as_view(), name='consumer-profile'),

    # Check username and email availability    
    path('api/check-availability/', views.check_email, name='check_availability'),

    # Password reset
    path('api/password-reset/', views.PassWordResetAPIView.as_view(), name='password_reset_request'),
    path('api/password-reset/confirm/<uid>/<token>/', views.PasswordResetConfirmAPIView.as_view(), name='password_reset_confirm'),


    # Logout
    path('api/logout/', views.LogoutAPIView.as_view(), name='api_logout'),
]