from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import CustomUser

class UserAPITestCase(APITestCase):
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

    def authenticate(self):
        response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "OldStrongPassword123!",
            },
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    # -------------------------
    # Register
    # -------------------------

    def test_register(self):
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
        self.assertEqual(response.data["user"]["email"], "jane@example.com")
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        user = CustomUser.objects.get(email="jane@example.com")
        self.assertTrue(user.check_password("StrongPassword123!"))

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

    # -------------------------
    # Login / Token
    # -------------------------

    def test_login(self):
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

    def test_login_with_wrong_password(self):
        response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_nonexistent_user(self):
        response = self.client.post(
            self.token_url,
            {
                "email": "doesnotexist@example.com",
                "password": "OldStrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        login_response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "OldStrongPassword123!",
            },
        )

        refresh = login_response.data["refresh"]

        response = self.client.post(
            self.refresh_url,
            {"refresh": refresh},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_requires_valid_token(self):
        response = self.client.post(
            self.refresh_url,
            {"refresh": "invalid-token"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------
    # Profile
    # -------------------------

    def test_profile_requires_authentication(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile(self):
        self.authenticate()

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["first_name"], "John")
        self.assertEqual(response.data["last_name"], "Doe")
        self.assertNotIn("password", response.data)

    def test_update_profile(self):
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
        self.assertEqual(self.user.email, "john@example.com")

    def test_partial_update_profile(self):
        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {"first_name": "Jane"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Doe")

    def test_profile_cannot_change_protected_fields(self):
        self.authenticate()

        response = self.client.patch(
            self.profile_url,
            {
                "email": "hacker@example.com",
                "plan": "PR",
                "premium_until": "2030-01-01",
                "first_name": "Jane",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.email, "john@example.com")
        self.assertEqual(self.user.plan, "FR")
        self.assertIsNone(self.user.premium_until)
        self.assertEqual(self.user.first_name, "Jane")

    def test_profile_does_not_expose_password(self):
        self.authenticate()

        response = self.client.get(self.profile_url)

        self.assertNotIn("password", response.data)

    # -------------------------
    # Change password
    # -------------------------

    def test_change_password(self):
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

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_rejects_wrong_old_password(self):
        self.authenticate()

        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "WrongPassword123!",
                "new_password": "NewStrongPassword123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)

    def test_change_password_rejects_weak_password(self):
        self.authenticate()

        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "OldStrongPassword123!",
                "new_password": "123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # -------------------------
    # Logout
    # -------------------------

    def test_logout(self):
        login_response = self.client.post(
            self.token_url,
            {
                "email": self.user.email,
                "password": "OldStrongPassword123!",
            },
        )

        access = login_response.data["access"]
        refresh = login_response.data["refresh"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        logout_url = reverse("logout")

        response = self.client.post(
            logout_url,
            {"refresh": refresh},
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.post(
            self.refresh_url,
            {"refresh": refresh},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_requires_authentication(self):
        logout_url = reverse("logout")

        response = self.client.post(
            logout_url,
            {"refresh": "invalid-token"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_requires_refresh_token(self):
        self.authenticate()

        logout_url = reverse("logout")

        response = self.client.post(logout_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

