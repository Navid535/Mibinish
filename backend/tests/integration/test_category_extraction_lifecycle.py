from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.saved_items.extraction.parser import ParsedContent
from apps.saved_items.models import Category, SavedItem, SavedItemCategory
from apps.users.models import CustomUser


def create_user(email="user1@example.com"):
    return CustomUser.objects.create_user(
        email=email,
        password="strong-pass-123",
        first_name="Test",
    )


class CategoryExtractionLifecycleIntegrationTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def _run_queued_extraction_synchronously(self, callbacks):
        from apps.saved_items.extraction.pipeline import run_extraction

        with patch("apps.saved_items.tasks.extract_content_task.delay") as mock_delay:
            mock_delay.side_effect = lambda item_id, version: run_extraction(
                item_id, version
            )
            for callback in callbacks:
                callback()

    @patch("apps.saved_items.extraction.pipeline.parse_fetch_result")
    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_full_lifecycle_create_extract_change_url_change_categories(
        self,
        mock_fetch,
        mock_parse,
    ):
        cat_movies = Category.objects.create(user=self.user, name="Movies")
        cat_todo = Category.objects.create(user=self.user, name="To Watch")

        mock_fetch.return_value = MagicMock()
        mock_parse.return_value = ParsedContent(
            metadata={"title": "Original Page"},
            body_text="Original body",
        )

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client.post(
                reverse("saved-item-list"),
                {
                    "name": "A movie review",
                    "url": "https://example.com/review",
                    "categories": [
                        {"category": cat_movies.id, "priority": 1},
                        {"category": cat_todo.id, "priority": 2},
                    ],
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item_id = response.data["id"]

        item = SavedItem.objects.get(pk=item_id)
        self.assertEqual(item.category_links.count(), 2)
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.PENDING)

        self._run_queued_extraction_synchronously(callbacks)

        item.refresh_from_db()
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)
        self.assertEqual(item.metadata["title"], "Original Page")
        self.assertEqual(item.extracted_content["body_text"], "Original body")
        self.assertEqual(item.category_links.count(), 2)  # دست‌نخورده

        mock_parse.return_value = ParsedContent(
            metadata={"title": "New Page"},
            body_text="New body",
        )
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client.patch(
                reverse("saved-item-detail", args=[item_id]),
                {"url": "https://example.com/new-review"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item.refresh_from_db()
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.PENDING)
        self.assertIsNone(item.extracted_content)
        self.assertIsNone(item.metadata)
        self.assertEqual(item.category_links.count(), 2)  # هنوز دست‌نخورده

        self._run_queued_extraction_synchronously(callbacks)

        item.refresh_from_db()
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)
        self.assertEqual(item.metadata["title"], "New Page")
        self.assertEqual(item.extracted_content["body_text"], "New body")

        response = self.client.patch(
            reverse("saved-item-detail", args=[item_id]),
            {"categories": [{"category": cat_movies.id, "priority": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item.refresh_from_db()
        self.assertEqual(item.category_links.count(), 1)
        self.assertEqual(item.category_links.first().category, cat_movies)
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)
        self.assertEqual(item.metadata["title"], "New Page")

    def test_cannot_attach_other_users_category_during_full_flow(self):
        other_user = create_user(email="other@example.com")
        other_category = Category.objects.create(user=other_user, name="Not yours")

        response = self.client.post(
            reverse("saved-item-list"),
            {
                "name": "Test",
                "url": "https://example.com/test",
                "categories": [{"category": other_category.id, "priority": 1}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SavedItem.objects.filter(name="Test").exists())

    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_extraction_failure_does_not_affect_categories(self, mock_fetch):
        from apps.saved_items.extraction.fetcher import FetchError

        cat = Category.objects.create(user=self.user, name="Reading")
        mock_fetch.side_effect = FetchError("host unreachable")

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client.post(
                reverse("saved-item-list"),
                {
                    "name": "Broken link",
                    "url": "https://broken.example.com",
                    "categories": [{"category": cat.id, "priority": 1}],
                },
                format="json",
            )
        item_id = response.data["id"]

        self._run_queued_extraction_synchronously(callbacks)

        item = SavedItem.objects.get(pk=item_id)
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.FAILED)
        self.assertEqual(item.category_links.count(), 1)
        self.assertEqual(item.category_links.first().category, cat)

    def test_deleting_category_removes_link_but_not_the_saved_item(self):
        cat = Category.objects.create(user=self.user, name="Temp")
        item = SavedItem.objects.create(
            user=self.user, name="Keep me", url="https://example.com/x"
        )
        SavedItemCategory.objects.create(saved_item=item, category=cat, priority=1)

        response = self.client.delete(reverse("category-detail", args=[cat.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        item.refresh_from_db()
        self.assertEqual(item.category_links.count(), 0)
        self.assertTrue(SavedItem.objects.filter(pk=item.pk).exists())
