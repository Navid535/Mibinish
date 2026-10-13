from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.saved_items.models import Category, SavedItem, SavedItemCategory
from apps.users.models import CustomUser


def create_user(email, first_name="Test"):
    return CustomUser.objects.create_user(
        email=email,
        password="strong-pass-123",
        first_name=first_name,
    )


class OwnershipLifecycleIntegrationTests(APITestCase):
    def setUp(self):
        self.user1 = create_user(
            "user1@example.com",
            first_name="User One",
        )
        self.user2 = create_user(
            "user2@example.com",
            first_name="User Two",
        )

        self.category1 = Category.objects.create(
            user=self.user1,
            name="User 1 Category",
        )

        self.item1 = SavedItem.objects.create(
            user=self.user1,
            name="User 1 Item",
            url="https://example.com/user1",
        )

        SavedItemCategory.objects.create(
            saved_item=self.item1,
            category=self.category1,
            priority=1,
        )

        self.category2 = Category.objects.create(
            user=self.user2,
            name="User 2 Category",
        )

        self.item2 = SavedItem.objects.create(
            user=self.user2,
            name="User 2 Item",
            url="https://example.com/user2",
        )

        SavedItemCategory.objects.create(
            saved_item=self.item2,
            category=self.category2,
            priority=1,
        )

        self.client.force_authenticate(user=self.user1)

    def test_user_cannot_cross_ownership_boundaries_across_full_lifecycle(self):
        response = self.client.get(reverse("category-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        category_names = [category["name"] for category in response.data["results"]]

        self.assertIn(
            "User 1 Category",
            category_names,
        )
        self.assertNotIn(
            "User 2 Category",
            category_names,
        )

        response = self.client.get(reverse("saved-item-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item_names = [item["name"] for item in response.data["results"]]

        self.assertIn(
            "User 1 Item",
            item_names,
        )
        self.assertNotIn(
            "User 2 Item",
            item_names,
        )

        response = self.client.get(
            reverse("category-detail", args=[self.category2.id]),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        response = self.client.get(
            reverse("saved-item-detail", args=[self.item2.id]),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        response = self.client.patch(
            reverse("category-detail", args=[self.category2.id]),
            {"name": "Hacked Category"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.category2.refresh_from_db()

        self.assertEqual(
            self.category2.name,
            "User 2 Category",
        )

        response = self.client.patch(
            reverse("saved-item-detail", args=[self.item2.id]),
            {"name": "Hacked Item"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.item2.refresh_from_db()

        self.assertEqual(
            self.item2.name,
            "User 2 Item",
        )

        self.assertEqual(
            self.item2.url,
            "https://example.com/user2",
        )

        response = self.client.patch(
            reverse("saved-item-detail", args=[self.item1.id]),
            {
                "categories": [
                    {
                        "category": self.category2.id,
                        "priority": 1,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.item1.refresh_from_db()

        category_ids = set(
            self.item1.category_links.values_list(
                "category_id",
                flat=True,
            )
        )

        self.assertIn(
            self.category1.id,
            category_ids,
        )

        self.assertNotIn(
            self.category2.id,
            category_ids,
        )

        self.category2.refresh_from_db()
        self.item2.refresh_from_db()

        self.assertEqual(
            self.category2.user_id,
            self.user2.id,
        )
        self.assertEqual(
            self.category2.name,
            "User 2 Category",
        )

        self.assertEqual(
            self.item2.user_id,
            self.user2.id,
        )
        self.assertEqual(
            self.item2.name,
            "User 2 Item",
        )

        self.assertEqual(
            self.item2.category_links.count(),
            1,
        )

        self.assertEqual(
            self.item2.category_links.first().category,
            self.category2,
        )
