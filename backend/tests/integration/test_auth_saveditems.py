from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import CustomUser


class AuthSavedItemsIntegrationTests(APITestCase):
    def _register_and_get_tokens(self, email="user1@example.com"):
        response = self.client.post(
            reverse("register"),
            {
                "email": email,
                "first_name": "Navid",
                "password": "SomeStrongPass123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["access"], response.data["refresh"]

    def _auth_header(self, access_token):
        return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}

    def test_full_flow_register_then_create_and_list_saved_item(self):
        access_token, _ = self._register_and_get_tokens()

        create_response = self.client.post(
            reverse("saved-item-list"),
            {"name": "First bookmark", "url": "https://example.com/article"},
            format="json",
            **self._auth_header(access_token),
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(
            reverse("saved-item-list"),
            **self._auth_header(access_token),
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in list_response.data["results"]]
        self.assertIn("First bookmark", names)

    def test_login_via_token_endpoint_then_used_on_saved_items(self):
        CustomUser.objects.create_user(
            email="existing@example.com",
            password="SomeStrongPass123!",
            first_name="Existing",
        )

        login_response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "email": "existing@example.com",
                "password": "SomeStrongPass123!",
            },
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        access_token = login_response.data["access"]

        response = self.client.get(
            reverse("saved-item-list"),
            **self._auth_header(access_token),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_token_produces_a_working_access_token(self):
        _, refresh_token = self._register_and_get_tokens()

        refresh_response = self.client.post(
            reverse("token_refresh"),
            {
                "refresh": refresh_token,
            },
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        new_access_token = refresh_response.data["access"]

        response = self.client.get(
            reverse("saved-item-list"),
            **self._auth_header(new_access_token),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_token_is_rejected_on_saved_items(self):
        response = self.client.get(
            reverse("saved-item-list"),
            HTTP_AUTHORIZATION="Bearer this.is.not.a.valid.token",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_from_one_user_cannot_see_another_users_items(self):
        access_token_1, _ = self._register_and_get_tokens(email="user1@example.com")
        access_token_2, _ = self._register_and_get_tokens(email="user2@example.com")

        self.client.post(
            reverse("saved-item-list"),
            {"name": "User1's item", "url": "https://example.com/1"},
            format="json",
            **self._auth_header(access_token_1),
        )

        response = self.client.get(
            reverse("saved-item-list"),
            **self._auth_header(access_token_2),
        )
        names = [item["name"] for item in response.data["results"]]
        self.assertNotIn("User1's item", names)
