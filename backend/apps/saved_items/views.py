from rest_framework import permissions, viewsets

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

    def get_queryset(self):
        return SavedItem.objects.visible_to(self.request.user)