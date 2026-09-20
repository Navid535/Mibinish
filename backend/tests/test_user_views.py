from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import CustomUser


class UserViewsTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            password="OldStrongPassword123!",
        )

        self.register_url = reverse("register")
        self.token_url = reverse("token_obtain_pair")
        self.refresh_url = reverse("token_refresh")
        self.profile_url = reverse("profile")
        self.change_password_url = reverse("change_password")
        self.logout_url = reverse("logout")

    def authenticate(self):
        response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "OldStrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    # ============================================================
    # Register
    # ============================================================

    def test_register_success(self):
        response = self.client.post(
            self.register_url,
            {
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "password": "StrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

        self.assertEqual(
            response.data["user"]["email"],
            "jane@example.com",
        )

        user = CustomUser.objects.get(email="jane@example.com")
        self.assertTrue(user.check_password("StrongPassword123!"))

    def test_register_does_not_require_authentication(self):
        response = self.client.post(
            self.register_url,
            {
                "email": "jane@example.com",
                "first_name": "Jane",
                "password": "StrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_requires_first_name(self):
        response = self.client.post(
            self.register_url,
            {
                "email": "jane@example.com",
                "password": "StrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", response.data)

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(
            self.register_url,
            {
                "email": self.user.email,
                "first_name": "Jane",
                "password": "StrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            self.register_url,
            {
                "email": "jane@example.com",
                "first_name": "Jane",
                "password": "123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_does_not_expose_password(self):
        response = self.client.post(
            self.register_url,
            {
                "email": "jane@example.com",
                "first_name": "Jane",
                "password": "StrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        self.assertNotIn("password", response.data.get("user", {}))

    # ============================================================
    # Login / Token
    # ============================================================

    def test_login_success(self):
        response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "OldStrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_rejects_nonexistent_user(self):
        response = self.client.post(
            self.token_url,
            {
                "email": "doesnotexist@example.com",
                "password": "OldStrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ============================================================
    # Refresh token
    # ============================================================

    def test_refresh_token_success(self):
        login_response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "OldStrongPassword123!",
            },
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        response = self.client.post(
            self.refresh_url,
            {"refresh": login_response.data["refresh"]},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_rejects_invalid_token(self):
        response = self.client.post(
            self.refresh_url,
            {"refresh": "invalid-token"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ============================================================
    # Profile - authentication
    # ============================================================

    def test_profile_requires_authentication(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ============================================================
    # Profile - retrieve
    # ============================================================

    def test_get_profile_returns_current_user(self):
        self.authenticate()

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["first_name"], "John")
        self.assertEqual(response.data["last_name"], "Doe")
        self.assertEqual(response.data["plan"], "FR")
        self.assertIsNone(response.data["premium_until"])

    def test_get_profile_does_not_expose_password(self):
        self.authenticate()

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("password", response.data)

    # ============================================================
    # Profile - update
    # ============================================================

    def test_update_profile_with_put(self):
        self.authenticate()

        response = self.client.put(
            self.profile_url,
            {
                "email": "changed@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Smith")

        # Email is read-only.
        self.assertEqual(self.user.email, "john@example.com")

    def test_partial_update_profile_with_patch(self):
        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {"first_name": "Jane"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Doe")

    def test_profile_protected_fields_cannot_be_changed(self):
        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {
                "email": "hacker@example.com",
                "plan": "PR",
                "premium_until": "2030-01-01",
                "id": 999999,
                "first_name": "Jane",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.email, "john@example.com")
        self.assertEqual(self.user.plan, "FR")
        self.assertIsNone(self.user.premium_until)
        self.assertEqual(self.user.id, response.data["id"])
        self.assertEqual(self.user.first_name, "Jane")

    # ============================================================
    # Profile - retention days
    # ============================================================

    def test_free_user_cannot_change_retention_days(self):
        self.authenticate()

        original_value = self.user.completed_items_retention_days

        response = self.client.patch(
            self.profile_url,
            {"completed_items_retention_days": 14},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "completed_items_retention_days",
            response.data,
        )

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.completed_items_retention_days,
            original_value,
        )

    def test_active_premium_user_can_change_retention_days(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() + timedelta(days=30)
        self.user.save(update_fields=["plan", "premium_until"])

        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {"completed_items_retention_days": 14},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.completed_items_retention_days,
            14,
        )

    def test_expired_premium_user_cannot_change_retention_days(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() - timedelta(days=1)
        self.user.save(update_fields=["plan", "premium_until"])

        self.authenticate()

        original_value = self.user.completed_items_retention_days

        response = self.client.patch(
            self.profile_url,
            {"completed_items_retention_days": 14},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "completed_items_retention_days",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.completed_items_retention_days,
            original_value,
        )

    def test_active_premium_user_can_set_minimum_retention_days(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() + timedelta(days=30)
        self.user.save(update_fields=["plan", "premium_until"])

        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {"completed_items_retention_days": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.completed_items_retention_days,
            1,
        )

    def test_active_premium_user_can_set_maximum_retention_days(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() + timedelta(days=30)
        self.user.save(update_fields=["plan", "premium_until"])

        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {"completed_items_retention_days": 31},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.completed_items_retention_days,
            31,
        )

    def test_active_premium_user_cannot_set_retention_days_below_minimum(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() + timedelta(days=30)
        self.user.save(update_fields=["plan", "premium_until"])

        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {"completed_items_retention_days": 0},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_active_premium_user_cannot_set_retention_days_above_maximum(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() + timedelta(days=30)
        self.user.save(update_fields=["plan", "premium_until"])

        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {"completed_items_retention_days": 32},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ============================================================
    # Change password
    # ============================================================

    def test_change_password_success(self):
        self.authenticate()

        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "OldStrongPassword123!",
                "new_password": "NewStrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password("NewStrongPassword123!")
        )
        self.assertFalse(
            self.user.check_password("OldStrongPassword123!")
        )

    def test_change_password_requires_authentication(self):
        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "OldStrongPassword123!",
                "new_password": "NewStrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_change_password_rejects_wrong_old_password(self):
        self.authenticate()

        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "WrongPassword123!",
                "new_password": "NewStrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("old_password", response.data)

    def test_change_password_rejects_weak_new_password(self):
        self.authenticate()

        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "OldStrongPassword123!",
                "new_password": "123",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("new_password", response.data)

    def test_change_password_only_allows_put(self):
        self.authenticate()

        response = self.client.patch(
            self.change_password_url,
            {
                "old_password": "OldStrongPassword123!",
                "new_password": "NewStrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # ============================================================
    # Logout
    # ============================================================

    def test_logout_success_blacklists_refresh_token(self):
        login_response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "OldStrongPassword123!",
            },
        )

        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
        )

        access = login_response.data["access"]
        refresh = login_response.data["refresh"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        response = self.client.post(
            self.logout_url,
            {"refresh": refresh},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        # The same refresh token must no longer be usable.
        response = self.client.post(
            self.refresh_url,
            {"refresh": refresh},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_requires_authentication(self):
        response = self.client.post(
            self.logout_url,
            {"refresh": "invalid-token"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_requires_refresh_token(self):
        self.authenticate()

        response = self.client.post(self.logout_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_logout_rejects_invalid_refresh_token(self):
        self.authenticate()

        response = self.client.post(
            self.logout_url,
            {"refresh": "invalid-token"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

