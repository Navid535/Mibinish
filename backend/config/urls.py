import os

from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from apps.core.views import health_check

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/auth/", include('apps.users.urls')),
    path("api/v1/", include('apps.saved_items.urls')),
    path("health/", health_check, name="health_checker"),

]

if settings.DEBUG:
    urlpatterns += [
        path(
            "api/schema/",
            SpectacularAPIView.as_view(),
            name="schema",
        ),

        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(
                url_name="schema"
            ),
            name="swagger-ui",
        ),
    ]
