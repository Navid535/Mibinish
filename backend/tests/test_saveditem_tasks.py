from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.saved_items.models import SavedItem
from apps.saved_items.tasks import purge_expired_completed_items
from apps.users.models import CustomUser


class PurgeExpiredCompletedItemsTaskTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com",
            password="testpass123",
            first_name="Test",
        )

    def create_item(self, *, status=SavedItem.Status.COMPLETED, completed_at=None):
        return SavedItem.objects.create(
            user=self.user,
            name="Test item",
            status=status,
            completed_at=completed_at,
        )

    def test_deletes_expired_completed_item(self):
        item = self.create_item(
            completed_at=timezone.now() - timedelta(days=8),
        )

        deleted_count = purge_expired_completed_items()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(SavedItem.objects.filter(pk=item.pk).exists())

    def test_deletes_item_exactly_at_retention_boundary(self):
        item = self.create_item(
            completed_at=timezone.now()
            - timedelta(days=self.user.completed_items_retention_days),
        )

        deleted_count = purge_expired_completed_items()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(SavedItem.objects.filter(pk=item.pk).exists())

    def test_keeps_completed_item_that_has_not_expired(self):
        item = self.create_item(
            completed_at=timezone.now() - timedelta(days=6),
        )

        deleted_count = purge_expired_completed_items()

        self.assertEqual(deleted_count, 0)
        self.assertTrue(SavedItem.objects.filter(pk=item.pk).exists())

    def test_does_not_delete_to_do_item(self):
        item = self.create_item(
            status=SavedItem.Status.TO_DO,
            completed_at=None,
        )

        deleted_count = purge_expired_completed_items()

        self.assertEqual(deleted_count, 0)
        self.assertTrue(SavedItem.objects.filter(pk=item.pk).exists())

    def test_retention_days_are_applied_per_user(self):
        self.user.completed_items_retention_days = 7
        self.user.save(update_fields=["completed_items_retention_days"])

        other_user = CustomUser.objects.create_user(
            email="other@example.com",
            password="testpass123",
            first_name="Other",
        )
        other_user.completed_items_retention_days = 30
        other_user.save(update_fields=["completed_items_retention_days"])

        old_item = SavedItem.objects.create(
            user=self.user,
            name="Old item",
            status=SavedItem.Status.COMPLETED,
            completed_at=timezone.now() - timedelta(days=8),
        )
        recent_for_other_user = SavedItem.objects.create(
            user=other_user,
            name="Recent item",
            status=SavedItem.Status.COMPLETED,
            completed_at=timezone.now() - timedelta(days=8),
        )

        deleted_count = purge_expired_completed_items()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(SavedItem.objects.filter(pk=old_item.pk).exists())
        self.assertTrue(SavedItem.objects.filter(pk=recent_for_other_user.pk).exists())

    def test_deletes_only_expired_items_and_returns_deleted_count(self):
        expired_item = self.create_item(
            completed_at=timezone.now() - timedelta(days=8),
        )
        active_item = self.create_item(
            completed_at=timezone.now() - timedelta(days=6),
        )
        todo_item = self.create_item(
            status=SavedItem.Status.TO_DO,
            completed_at=None,
        )

        deleted_count = purge_expired_completed_items()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(SavedItem.objects.filter(pk=expired_item.pk).exists())
        self.assertTrue(SavedItem.objects.filter(pk=active_item.pk).exists())
        self.assertTrue(SavedItem.objects.filter(pk=todo_item.pk).exists())
