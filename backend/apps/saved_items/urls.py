from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.saved_items.views import CategoryViewSet, SavedItemViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("saved-items", SavedItemViewSet, basename="saved-item")

urlpatterns = [
    path("", include(router.urls)),
]
