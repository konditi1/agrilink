from django_filters import rest_framework as filters
from .models import Category, Product
from django.db.models import Q

class CategoryFilter(filters.FilterSet):
    """FilterSet for filtering categories."""
    
    parent = filters.CharFilter(method="filter_parent")
    has_products = filters.BooleanFilter(method="filter_has_products")

    class Meta:
        model = Category
        fields = ["parent", "has_products"]

    def filter_parent(self, queryset, name, value):
        """Filter root categories if `parent=null` or `parent=root` is passed."""
        if value in ["null", "root"]:
            return queryset.filter(parent__isnull=True)
        return queryset.filter(Q(parent=value) | Q(parent__slug=value))

    def filter_has_products(self, queryset, name, value):
        """Filter categories that have products."""
        if value:
            return queryset.filter(Q(products__isnull=False)).distinct()
        return queryset


class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    seller = filters.CharFilter(field_name="seller__id")  # Filter by seller ID
    farm_name = filters.CharFilter(method="filter_by_farm_name")
    in_stock = filters.BooleanFilter(method="filter_in_stock")
    show_all = filters.BooleanFilter(method="filter_show_all")
    ordering = filters.OrderingFilter(fields={
                                        'price': 'price',
                                        'stock_quantity': 'stock_quantity',
                                        'created_at': 'created_at',
                                    }
                                )
    class Meta:
        model = Product
        fields = ["category",  "is_organic"]
        order_by = ["price", "stock_quantity", "created_at"]

    def filter_by_farm_name(self, queryset, name, value):
        """
        Filter products by farm name.

        Returns a queryset of products whose seller's farm name contains the
        given value (case-insensitive).
        """
        return queryset.filter(Q(seller__farm_name__icontains=value) | Q(seller__company_name__icontains=value))

    def filter_in_stock(self, queryset, name, value):
        """
        Filter products that are in stock.

        If `value` is True, filters products that have a stock quantity greater than 0
        and are active. Otherwise, returns the full queryset.
        """
        if value:
            return queryset.filter(Q(stock_quantity__gt=0) & Q(is_available=True))
        return queryset

