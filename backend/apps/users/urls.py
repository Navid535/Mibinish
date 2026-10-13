from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import (
    RegisterView,
    ProfileView,
    ChangePasswordView,
    SetPasswordView,
    LogoutView,
    ThrottledTokenObtainPairView,
    GoogleLoginView,
)


urlpatterns = [
    path('token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('google/', GoogleLoginView.as_view(), name='google_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('register/', RegisterView.as_view(), name='register'),
    
    path('me/', ProfileView.as_view(), name='profile'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path("me/set-password/", SetPasswordView.as_view(), name="set_password"),

    path("logout/", LogoutView.as_view(), name="logout"),
]
