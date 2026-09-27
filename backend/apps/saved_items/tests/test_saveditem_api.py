from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.saved_items.models import Category, SavedItem
from apps.users.models import CustomUser


def create_user(
    email="user@example.com",
    password="strong-pass-123",
    first_name="Test",
):
    return CustomUser.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
    )


class SavedItemAPITests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(
            email="other@example.com",
            first_name="Other",
        )

        self.client.force_authenticate(self.user)

        self.list_url = reverse("saved-item-list")

    def detail_url(self, item):
        return reverse("saved-item-detail", args=[item.pk])

    def create_item(self, **kwargs):
        defaults = {
            "name": "Test Item",
            "url": "https://example.com/article",
        }
        defaults.update(kwargs)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.list_url,
                defaults,
                format="json",
            )

        return response

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    @patch("apps.saved_items.tasks.extract_content_task.delay")
    def test_create_saved_item_with_url(self, mock_delay):
        response = self.create_item(
            name="Django",
            url="https://example.com/django",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        item = SavedItem.objects.get(pk=response.data["id"])

        self.assertEqual(item.user, self.user)
        self.assertEqual(item.name, "Django")
        self.assertEqual(item.url, "https://example.com/django")
        self.assertEqual(
            item.extraction_status,
            SavedItem.ExtractionStatus.PENDING,
        )

        mock_delay.assert_called_once_with(item.id, str(item.extraction_version))


    def test_create_saved_item_without_url(self):
        response = self.create_item(
            name="A manual note",
            url=None,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        item = SavedItem.objects.get(pk=response.data["id"])

        self.assertEqual(
            item.extraction_status,
            SavedItem.ExtractionStatus.NO_URL,
        )
        self.assertIsNone(item.extracted_content)
        self.assertIsNone(item.metadata)

    def test_create_saved_item_requires_name_or_url(self):
        response = self.client.post(
            self.list_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_saved_item_belongs_to_authenticated_user(self):
        response = self.create_item()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        item = SavedItem.objects.get(pk=response.data["id"])

        self.assertEqual(item.user, self.user)

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def test_list_returns_only_current_users_items(self):
        own_item = SavedItem.objects.create(
            user=self.user,
            name="Mine",
            url="https://example.com/mine",
        )

        SavedItem.objects.create(
            user=self.other_user,
            name="Not Mine",
            url="https://example.com/other",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = {item["id"] for item in response.data["results"]}

        self.assertIn(own_item.id, ids)

        other_item = SavedItem.objects.get(
            user=self.other_user,
        )
        self.assertNotIn(other_item.id, ids)

    def test_list_is_paginated(self):
        SavedItem.objects.bulk_create(
            [
                SavedItem(
                    user=self.user,
                    name=f"Item {i}",
                    url=f"https://example.com/{i}",
                )
                for i in range(25)
            ]
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 25)

    # ------------------------------------------------------------------
    # RETRIEVE
    # ------------------------------------------------------------------

    def test_retrieve_own_item(self):
        item = SavedItem.objects.create(
            user=self.user,
            name="Mine",
            url="https://example.com/mine",
        )

        response = self.client.get(self.detail_url(item))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], item.id)
        self.assertEqual(response.data["name"], "Mine")

    def test_retrieve_other_users_item_returns_404(self):
        item = SavedItem.objects.create(
            user=self.other_user,
            name="Other",
            url="https://example.com/other",
        )

        response = self.client.get(self.detail_url(item))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    @patch("apps.saved_items.tasks.extract_content_task.delay")
    def test_update_url_resets_extraction_and_queues_task(
        self,
        mock_delay,
    ):
        item = SavedItem.objects.create(
            user=self.user,
            name="Old",
            url="https://example.com/old",
            extraction_status=SavedItem.ExtractionStatus.DONE,
            extracted_content={"body_text": "old content"},
            metadata={"title": "Old"},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                self.detail_url(item),
                {
                    "url": "https://example.com/new",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item.refresh_from_db()

        self.assertEqual(item.url, "https://example.com/new")
        self.assertEqual(
            item.extraction_status,
            SavedItem.ExtractionStatus.PENDING,
        )
        self.assertIsNone(item.extracted_content)
        self.assertIsNone(item.metadata)
        self.assertIsNone(item.extraction_error)

        mock_delay.assert_called_once_with(item.id, str(item.extraction_version))


    @patch("apps.saved_items.tasks.extract_content_task.delay")
    def test_remove_url_sets_no_url_and_does_not_queue_task(
        self,
        mock_delay,
    ):
        item = SavedItem.objects.create(
            user=self.user,
            name="Manual",
            url="https://example.com/old",
            extraction_status=SavedItem.ExtractionStatus.DONE,
            extracted_content={"body_text": "old content"},
            metadata={"title": "Old"},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                self.detail_url(item),
                {
                    "url": None,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item.refresh_from_db()

        self.assertIsNone(item.url)
        self.assertEqual(
            item.extraction_status,
            SavedItem.ExtractionStatus.NO_URL,
        )
        self.assertIsNone(item.extracted_content)
        self.assertIsNone(item.metadata)
        self.assertIsNone(item.extraction_error)

        mock_delay.assert_not_called()

    def test_update_other_users_item_returns_404(self):
        item = SavedItem.objects.create(
            user=self.other_user,
            name="Other",
            url="https://example.com/other",
        )

        response = self.client.patch(
            self.detail_url(item),
            {"name": "Hacked"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        item.refresh_from_db()
        self.assertEqual(item.name, "Other")

    # ------------------------------------------------------------------
    # EXTRACTION STATE
    # ------------------------------------------------------------------

    def test_extraction_fields_are_read_only(self):
        item = SavedItem.objects.create(
            user=self.user,
            name="Test",
            url="https://example.com/test",
            extraction_status=SavedItem.ExtractionStatus.DONE,
            extraction_error=None,
        )

        response = self.client.patch(
            self.detail_url(item),
            {
                "extraction_status": SavedItem.ExtractionStatus.FAILED,
                "extraction_error": "Fake error",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        item.refresh_from_db()

        self.assertEqual(
            item.extraction_status,
            SavedItem.ExtractionStatus.DONE,
        )
        self.assertIsNone(item.extraction_error)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def test_delete_own_item(self):
        item = SavedItem.objects.create(
            user=self.user,
            name="Delete me",
            url="https://example.com/delete",
        )

        response = self.client.delete(self.detail_url(item))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            SavedItem.objects.filter(pk=item.pk).exists()
        )

    def test_delete_other_users_item_returns_404(self):
        item = SavedItem.objects.create(
            user=self.other_user,
            name="Do not delete",
            url="https://example.com/protected",
        )

        response = self.client.delete(self.detail_url(item))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            SavedItem.objects.filter(pk=item.pk).exists()
        )

    # ------------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------------

    def test_unauthenticated_list_is_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_create_is_rejected(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.list_url,
            {
                "name": "Test",
                "url": "https://example.com/test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(
        "apps.saved_items.tasks.extract_content_task.delay",
        side_effect=ConnectionRefusedError("broker down"),
    )
    def test_create_saved_item_succeeds_even_if_broker_is_down(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.create_item(name="Resilience test", url="https://example.com/x")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # نه ۵۰۰!

        item = SavedItem.objects.get(pk=response.data["id"])
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.FAILED)