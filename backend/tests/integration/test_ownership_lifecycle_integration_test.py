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
    """
    یک سناریوی کامل ownership بین دو کاربر را دنبال می‌کند.

    ```
    User 1 و User 2 هرکدام category و SavedItem خودشان را دارند.
    سپس User 1 در یک flow متوالی تلاش می‌کند از مسیرهای مختلف به
    منابع User 2 دسترسی پیدا کند:

        list categories
        list saved items
        retrieve category
        update category
        retrieve saved item
        update saved item
        attach other's category to own item
        replace own item's categories with other's category

    هیچ‌کدام نباید اجازه‌ی دسترسی یا تغییر منابع User 2 را بدهند.
    """

    def setUp(self):
        self.user1 = create_user(
            "user1@example.com",
            first_name="User One",
        )
        self.user2 = create_user(
            "user2@example.com",
            first_name="User Two",
        )

        # ---------------------------------------------------------
        # User 1 resources
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # User 2 resources
        # ---------------------------------------------------------
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

        # کل سناریو را از دید User 1 اجرا می‌کنیم.
        self.client.force_authenticate(user=self.user1)

    def test_user_cannot_cross_ownership_boundaries_across_full_lifecycle(self):
        # =========================================================
        # 1. LIST
        # =========================================================
        # User 1 باید فقط category خودش را ببیند.
        response = self.client.get(reverse("category-list"))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        category_names = [
            category["name"]
            for category in response.data["results"]
        ]

        self.assertIn(
            "User 1 Category",
            category_names,
        )
        self.assertNotIn(
            "User 2 Category",
            category_names,
        )

        # User 1 باید فقط SavedItem خودش را ببیند.
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

        # =========================================================
        # 2. RETRIEVE
        # =========================================================
        # User 1 نمی‌تواند category متعلق به User 2 را retrieve کند.
        response = self.client.get(
            reverse("category-detail", args=[self.category2.id]),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # User 1 نمی‌تواند SavedItem متعلق به User 2 را retrieve کند.
        response = self.client.get(
            reverse("saved-item-detail", args=[self.item2.id]),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # =========================================================
        # 3. UPDATE
        # =========================================================
        # تلاش برای تغییر category کاربر دیگر.
        response = self.client.patch(
            reverse("category-detail", args=[self.category2.id]),
            {"name": "Hacked Category"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # مطمئن شو واقعاً تغییری ایجاد نشده.
        self.category2.refresh_from_db()

        self.assertEqual(
            self.category2.name,
            "User 2 Category",
        )

        # تلاش برای تغییر SavedItem کاربر دیگر.
        response = self.client.patch(
            reverse("saved-item-detail", args=[self.item2.id]),
            {"name": "Hacked Item"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # مطمئن شو item هم دست‌نخورده مانده.
        self.item2.refresh_from_db()

        self.assertEqual(
            self.item2.name,
            "User 2 Item",
        )

        self.assertEqual(
            self.item2.url,
            "https://example.com/user2",
        )

        # =========================================================
        # 4. ATTACH OTHER USER'S CATEGORY
        # =========================================================
        # User 1 مالک item خودش است، اما category متعلق به User 2 است.
        #
        # این مهم است چون صرفاً ownership روی SavedItem کافی نیست؛
        # باید ownership رابطه‌ی category را هم enforce کنیم.
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

        # رابطه‌ی قبلی نباید از بین رفته باشد.
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

        # =========================================================
        # 5. CROSS-USER RESOURCE MUST REMAIN COMPLETELY INTACT
        # =========================================================
        # بعد از تمام تلاش‌های بالا، resources کاربر دوم را
        # دوباره مستقیم بررسی می‌کنیم.
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
