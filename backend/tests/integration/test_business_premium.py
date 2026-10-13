from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin, messages
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
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

    def _activate_premium_through_admin(self, user, days=30):
        factory = RequestFactory()

        request = factory.post(
            reverse("admin:users_customuser_changelist"),
            {
                "apply": "1",
                "days": days,
                "_selected_action": [str(user.pk)],
            },
        )

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
        self.user.refresh_from_db()

        self.assertEqual(self.user.plan, "FR")
        self.assertEqual(
            self.user.completed_items_retention_days,
            7,
        )
        self.assertIsNone(self.user.premium_until)

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

        self._activate_premium_through_admin(
            self.user,
            days=30,
        )

        self.user.refresh_from_db()

        self.assertEqual(self.user.plan, "PR")
        self.assertIsNotNone(self.user.premium_until)

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

        old_item.completed_at = timezone.now() - timedelta(days=15)
        old_item.save(update_fields=["completed_at"])

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

        self.assertTrue(SavedItem.objects.filter(pk=old_item_id).exists())
        self.assertTrue(SavedItem.objects.filter(pk=recent_item_id).exists())

        purge_expired_completed_items()

        self.assertFalse(SavedItem.objects.filter(pk=old_item_id).exists())

        self.assertTrue(SavedItem.objects.filter(pk=recent_item_id).exists())
