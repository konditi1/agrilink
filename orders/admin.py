from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'is_paid', 'total_price', 'status', 'created_at', 'updated_at'
    ]
    list_filter = ['is_paid', 'status', 'created_at', 'updated_at']
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        """Automatically calculate total price before saving."""
        obj.total_price = sum(item.get_total() for item in obj.items.all())
        super().save_model(request, obj, form, change)
