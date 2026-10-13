import django_filters

from apps.saved_items.models import SavedItem


class SavedItemFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(
        field_name="categories",
        lookup_expr="exact",
        label="Category ID",
    )
    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    completed_after = django_filters.DateTimeFilter(
        field_name="completed_at", lookup_expr="gte"
    )
    completed_before = django_filters.DateTimeFilter(
        field_name="completed_at", lookup_expr="lte"
    )

    class Meta:
        model = SavedItem
        fields = ("status", "source", "category")
