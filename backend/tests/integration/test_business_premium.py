from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin, messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.saved_items.models import SavedItem
from apps.saved_items.tasks import purge_expired_completed_items
from apps.users.admin import CustomUserAdmin
from apps.users.models import CustomUser

def create_user(email="[user1@example.com](mailto:user1@example.com)"):
    return CustomUser.objects.create_user(
    email=email,
    password="strong-pass-123",
    first_name="Test",
    )

class PremiumRetentionPurgeIntegrationTests(APITestCase):
    """
    زنجیره‌ی کامل:


        Free user
            ↓
        retention پیش‌فرض 7 روز
            ↓
        Premium شدن از طریق Admin Action واقعی
            ↓
        تغییر retention از طریق Profile API
            ↓
        ساخت SavedItem
            ↓
        complete کردن SavedItem از طریق API
            ↓
        شبیه‌سازی گذشت زمان با completed_at
            ↓
        اجرای purge
            ↓
        بررسی حذف/باقی‌ماندن آیتم بر اساس retention جدید
    """

    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

    def _activate_premium_through_admin(self, user, days=30):
        """
        همان CustomUserAdmin.activate_premium_action واقعی را اجرا می‌کند.

        Admin action یک endpoint HTTP معمولی نیست، بنابراین request مربوط
        به action را با RequestFactory شبیه‌سازی می‌کنیم.
        """
        factory = RequestFactory()

        request = factory.post(
            reverse("admin:users_customuser_changelist"),
            {
                "apply": "1",
                "days": days,
                "_selected_action": [str(user.pk)],
            },
        )

        # Admin action برای message_user به session/messages نیاز دارد.
        middleware = SessionMiddleware(lambda request: None)
        middleware.process_request(request)
        request.session.save()

        messages_middleware = messages.middleware.MessageMiddleware(
            lambda request: None
        )
        messages_middleware.process_request(request)

        request.user = CustomUser.objects.get(pk=user.pk)

        admin_instance = CustomUserAdmin(CustomUser, admin.site)

        queryset = CustomUser.objects.filter(pk=user.pk)

        with patch(
            "apps.users.admin.render",
            return_value=None,
        ):
            admin_instance.activate_premium_action(
                request,
                queryset,
            )

    def test_free_user_becomes_premium_changes_retention_and_purge_uses_new_retention(
        self,
    ):
        # ---------------------------------------------------------
        # 1. کاربر تازه ساخته شده و Free است
        # ---------------------------------------------------------
        self.user.refresh_from_db()

        self.assertEqual(self.user.plan, "FR")
        self.assertEqual(
            self.user.completed_items_retention_days,
            7,
        )
        self.assertIsNone(self.user.premium_until)

        # ---------------------------------------------------------
        # 2. Free user نمی‌تواند retention را تغییر دهد
        # ---------------------------------------------------------
        response = self.client.patch(
            reverse("profile"),
            {
                "completed_items_retention_days": 14,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.completed_items_retention_days,
            7,
        )

        # ---------------------------------------------------------
        # 3. همان کاربر را از طریق Admin Action واقعی Premium می‌کنیم
        # ---------------------------------------------------------
        self._activate_premium_through_admin(
            self.user,
            days=30,
        )

        self.user.refresh_from_db()

        self.assertEqual(self.user.plan, "PR")
        self.assertIsNotNone(self.user.premium_until)

        # ---------------------------------------------------------
        # 4. حالا Premium user retention را به 14 روز تغییر می‌دهد
        # ---------------------------------------------------------
        new_retention = 14

        response = self.client.patch(
            reverse("profile"),
            {
                "completed_items_retention_days": new_retention,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.completed_items_retention_days,
            new_retention,
        )

        # ---------------------------------------------------------
        # 5. یک SavedItem واقعی از طریق API می‌سازیم
        # ---------------------------------------------------------
        response = self.client.post(
            reverse("saved-item-list"),
            {
                "name": "Old completed item",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        old_item_id = response.data["id"]

        # ---------------------------------------------------------
        # 6. آیتم را از طریق API completed می‌کنیم
        # ---------------------------------------------------------
        response = self.client.patch(
            reverse("saved-item-detail", args=[old_item_id]),
            {
                "status": "completed",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        old_item = SavedItem.objects.get(pk=old_item_id)

        self.assertEqual(
            old_item.status,
            SavedItem.Status.COMPLETED,
        )
        self.assertIsNotNone(old_item.completed_at)

        # ---------------------------------------------------------
        # 7. زمان completed_at را 15 روز به عقب می‌بریم.
        #
        # retention فعلی = 14 روز
        # بنابراین این آیتم باید purge شود.
        # ---------------------------------------------------------
        old_item.completed_at = timezone.now() - timedelta(days=15)
        old_item.save(update_fields=["completed_at"])

        # ---------------------------------------------------------
        # 8. یک آیتم 10 روزه هم می‌سازیم.
        #
        # با retention جدید 14 روز:
        #     10 < 14
        #
        # پس باید باقی بماند.
        # ---------------------------------------------------------
        response = self.client.post(
            reverse("saved-item-list"),
            {
                "name": "Recent completed item",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        recent_item_id = response.data["id"]

        response = self.client.patch(
            reverse("saved-item-detail", args=[recent_item_id]),
            {
                "status": "completed",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        recent_item = SavedItem.objects.get(pk=recent_item_id)

        self.assertEqual(
            recent_item.status,
            SavedItem.Status.COMPLETED,
        )
        self.assertIsNotNone(recent_item.completed_at)

        recent_item.completed_at = timezone.now() - timedelta(days=10)
        recent_item.save(update_fields=["completed_at"])

        # ---------------------------------------------------------
        # 9. قبل از purge هر دو باید وجود داشته باشند
        # ---------------------------------------------------------
        self.assertTrue(
            SavedItem.objects.filter(pk=old_item_id).exists()
        )
        self.assertTrue(
            SavedItem.objects.filter(pk=recent_item_id).exists()
        )

        # ---------------------------------------------------------
        # 10. purge واقعی را اجرا می‌کنیم
        # ---------------------------------------------------------
        purge_expired_completed_items()

        # ---------------------------------------------------------
        # 11. آیتم 15 روزه باید حذف شده باشد
        # ---------------------------------------------------------
        self.assertFalse(
            SavedItem.objects.filter(pk=old_item_id).exists()
        )

        # ---------------------------------------------------------
        # 12. آیتم 10 روزه باید باقی مانده باشد
        #
        # اگر purge به اشتباه هنوز retention پیش‌فرض 7 روز را
        # استفاده کند، این آیتم هم حذف می‌شود.
        # ---------------------------------------------------------
        self.assertTrue(
            SavedItem.objects.filter(pk=recent_item_id).exists()
        )
