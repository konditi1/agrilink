from django_filters import rest_framework as filters
from .models import Category

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
        return queryset.filter(parent=value)

    def filter_has_products(self, queryset, name, value):
        """Filter categories that have products."""
        if value:
            return queryset.filter(products__isnull=False).distinct()
        return queryset
