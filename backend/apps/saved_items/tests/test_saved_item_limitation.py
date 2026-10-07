from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.saved_items.models import SavedItem
from apps.saved_items.services import (
    FREE_ITEM_LIMIT,
    PREMIUM_ITEM_LIMIT,
    create_saved_item,
)

User = get_user_model()


class CreateSavedItemQuotaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="StrongPassword123!",
            first_name="Monica",
            last_name="Geller",
        )

    def test_free_user_can_create_item_under_limit(self):
        SavedItem.objects.create(
            user=self.user,
            name="Existing item",
        )

        item = create_saved_item(
            user=self.user,
            name="New item",
        )

        self.assertEqual(item.name, "New item")

    def test_free_user_cannot_exceed_item_limit(self):
        SavedItem.objects.bulk_create(
            [
                SavedItem(
                    user=self.user,
                    name=f"Item {i}",
                )
                for i in range(FREE_ITEM_LIMIT)
            ]
        )

        with self.assertRaises(ValidationError):
            create_saved_item(
                user=self.user,
                name="One item too many",
            )

        self.assertEqual(
            SavedItem.objects.filter(user=self.user).count(),
            FREE_ITEM_LIMIT,
        )

    def test_premium_user_has_higher_limit(self):
        self.user.plan = "PR"
        self.user.save(update_fields=["plan"])

        SavedItem.objects.bulk_create(
            [
                SavedItem(
                    user=self.user,
                    name=f"Item {i}",
                )
                for i in range(FREE_ITEM_LIMIT)
            ]
        )

        item = create_saved_item(
            user=self.user,
            name="Premium item",
        )

        self.assertEqual(item.name, "Premium item")