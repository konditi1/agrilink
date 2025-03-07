from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum

from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Categories.
    """
    list_display = [
        'name', 
        'slug', 
        'parent', 
        'product_count', 
        'created_at', 
        'is_approved', 
        'approve_button',
        'updated_at'
    ]
    list_filter = ['is_approved', 'parent', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    actions = ['approve_selected']
    
    def get_queryset(self, request):
        """
        Optimize queryset with annotated product count.
        """
        return super().get_queryset(request).annotate(
            product_count=Count('products', distinct=True)
        )
    
    def product_count(self, obj):
        """
        Display number of products in the category.
        """
        return obj.product_count
    product_count.short_description = 'Product Count'
    product_count.admin_order_field = 'product_count'

    def approve_button(self, obj):
        """
        Display an 'Approve' button for pending categories.
        """
        if not obj.is_approved:
            return format_html(
                '<a class="button" href="{}">Approve</a>',
                f"/admin/shop/category/{obj.id}/approve/"
            )
        return "✔ Approved"
    approve_button.short_description = 'Approval'

    def approve_selected(self, request, queryset):
        """
        Bulk approve selected categories.
        """
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} categories approved.")
    approve_selected.short_description = "Approve selected categories"




class ProductImageInline(admin.TabularInline):
    """
    Inline admin for product images.
    """
    model = ProductImage
    extra = 1
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        """
        Display a thumbnail of the image.
        """
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return '(No image)'
    image_preview.short_description = 'Preview'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Comprehensive admin interface for Products.
    """
    list_display = [
        'name', 
        'seller', 
        'category', 
        'price', 
        'stock_quantity', 
        'is_organic', 
        'is_available', 
        'total_sales_value'
    ]
    list_filter = [
        'category', 
        'is_organic', 
        'is_available', 
        'created_at'
    ]
    search_fields = ['name', 'description', 'seller__username']
    
    # Include product images inline
    inlines = [ProductImageInline]
    
    # Auto-generate slug from name
    prepopulated_fields = {'slug': ('name',)}
    
    # Fieldsets for better organization
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'slug', 'description', 
                'category', 'seller'
            )
        }),
        ('Pricing and Availability', {
            'fields': (
                'price', 'unit', 'stock_quantity', 
                'is_organic', 'is_available'
            )
        }),
    )
    
    def get_queryset(self, request):
        """
        Optimize queryset with annotations.
        """
        return super().get_queryset(request).select_related(
            'seller', 'category'
        ).annotate(
            total_sales=Sum('stock_quantity')
        )
    
    def total_sales_value(self, obj):
        """
        Calculate and display total sales value.
        """
        return f"${obj.price * obj.stock_quantity:.2f}"
    total_sales_value.short_description = 'Total Value'
    total_sales_value.admin_order_field = 'total_sales'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Admin interface for Product Images.
    """
    list_display = [
        'product', 
        'image_preview', 
        'is_primary', 
        'alt_text'
    ]
    list_filter = ['is_primary', 'product__category']
    search_fields = ['product__name', 'alt_text']
    
    def image_preview(self, obj):
        """
        Display a thumbnail of the image.
        """
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return '(No image)'
    image_preview.short_description = 'Preview'