from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from apps.saved_items.filters import SavedItemFilter
from apps.saved_items.models import Category, SavedItem
from apps.saved_items.serializers import CategorySerializer, SavedItemSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Category.objects.visible_to(self.request.user)


class SavedItemViewSet(viewsets.ModelViewSet):
    serializer_class = SavedItemSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = SavedItemFilter
    search_fields = ('name', 'url', 'source')
    ordering_fields = ('created_at', 'completed_at', 'name')
    ordering = ('-created_at',)

    def get_queryset(self):
        return SavedItem.objects.visible_to(self.request.user)