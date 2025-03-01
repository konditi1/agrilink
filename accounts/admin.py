from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, FarmerProfile, ConsumerProfile

# Customizing the CustomUser admin panel
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'role', 'is_staff', 'is_active')
    search_fields = ('email', 'role')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('role', 'phone', 'profile_picture')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_staff', 'is_active')}
        ),
    )

# Admin for FarmerProfile
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'farm_name', 'farm_location', 'farm_size', 'products')
    search_fields = ('user__email', 'farm_name', 'products')

# Admin for ConsumerProfile
class ConsumerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_products', 'delivery_address')
    search_fields = ('user__email', 'preferred_products')

# Register all models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(FarmerProfile, FarmerProfileAdmin)
admin.site.register(ConsumerProfile, ConsumerProfileAdmin)
