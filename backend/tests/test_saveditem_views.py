from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.saved_items.models import Category, SavedItem
from apps.users.models import CustomUser


def create_user(email, first_name="Test"):
    return CustomUser.objects.create_user(
        email=email,
        password="strong-pass-123",
        first_name=first_name,
    )


class CategoryCRUDTests(APITestCase):
    def setUp(self):
        self.user = create_user("user1@example.com")
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("category-list")

    def test_create_category(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Games",
                "color": "#ff0000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        category = Category.objects.get(id=response.data["id"])

        self.assertEqual(category.user, self.user)
        self.assertEqual(category.name, "Games")
        self.assertEqual(category.color, "#ff0000")

    def test_list_categories(self):
        Category.objects.create(
            user=self.user,
            name="A",
        )
        Category.objects.create(
            user=self.user,
            name="B",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_categories_is_paginated(self):
        for index in range(25):
            Category.objects.create(
                user=self.user,
                name=f"Category {index}",
            )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_retrieve_category(self):
        category = Category.objects.create(
            user=self.user,
            name="A",
        )

        response = self.client.get(
            reverse("category-detail", args=[category.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "A")

    def test_update_category(self):
        category = Category.objects.create(
            user=self.user,
            name="A",
        )

        response = self.client.patch(
            reverse("category-detail", args=[category.id]),
            {"name": "B"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        category.refresh_from_db()

        self.assertEqual(category.name, "B")

    def test_delete_category(self):
        category = Category.objects.create(
            user=self.user,
            name="A",
        )

        response = self.client.delete(
            reverse("category-detail", args=[category.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Category.objects.filter(id=category.id).exists()
        )


class SavedItemCRUDTests(APITestCase):
    def setUp(self):
        self.user = create_user("user1@example.com")
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("saved-item-list")

    def test_create_saved_item_with_name(self):
        response = self.client.post(
            self.list_url,
            {"name": "Article"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        item = SavedItem.objects.get(id=response.data["id"])

        self.assertEqual(item.user, self.user)
        self.assertEqual(item.name, "Article")

    def test_create_saved_item_with_url(self):
        response = self.client.post(
            self.list_url,
            {"url": "https://example.com/article"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        item = SavedItem.objects.get(id=response.data["id"])

        self.assertEqual(
            item.url,
            "https://example.com/article",
        )

    def test_create_saved_item_without_name_or_url_fails(self):
        response = self.client.post(
            self.list_url,
            {},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_list_saved_items(self):
        SavedItem.objects.create(
            user=self.user,
            name="A",
        )
        SavedItem.objects.create(
            user=self.user,
            name="B",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_retrieve_saved_item(self):
        item = SavedItem.objects.create(
            user=self.user,
            name="A",
        )

        response = self.client.get(
            reverse("saved-item-detail", args=[item.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["name"], "A")

    def test_update_saved_item(self):
        item = SavedItem.objects.create(
            user=self.user,
            name="A",
        )

        response = self.client.patch(
            reverse("saved-item-detail", args=[item.id]),
            {"name": "B"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item.refresh_from_db()

        self.assertEqual(item.name, "B")

    def test_delete_saved_item(self):
        item = SavedItem.objects.create(
            user=self.user,
            name="A",
        )

        response = self.client.delete(
            reverse("saved-item-detail", args=[item.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            SavedItem.objects.filter(id=item.id).exists()
        )


class UnauthenticatedAccessTests(APITestCase):
    def test_category_list_requires_authentication(self):
        response = self.client.get(
            reverse("category-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_category_create_requires_authentication(self):
        response = self.client.post(
            reverse("category-list"),
            {"name": "A"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_category_retrieve_requires_authentication(self):
        response = self.client.get(
            reverse("category-detail", args=[1])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_category_update_requires_authentication(self):
        response = self.client.patch(
            reverse("category-detail", args=[1]),
            {"name": "A"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_category_delete_requires_authentication(self):
        response = self.client.delete(
            reverse("category-detail", args=[1])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_saved_item_list_requires_authentication(self):
        response = self.client.get(
            reverse("saved-item-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_saved_item_create_requires_authentication(self):
        response = self.client.post(
            reverse("saved-item-list"),
            {"name": "A"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_saved_item_retrieve_requires_authentication(self):
        response = self.client.get(
            reverse("saved-item-detail", args=[1])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_saved_item_update_requires_authentication(self):
        response = self.client.patch(
            reverse("saved-item-detail", args=[1]),
            {"name": "A"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_saved_item_delete_requires_authentication(self):
        response = self.client.delete(
            reverse("saved-item-detail", args=[1])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class CrossUserOwnershipTests(APITestCase):
    def setUp(self):
        self.user1 = create_user(
            "user1@example.com",
            first_name="User1",
        )
        self.user2 = create_user(
            "user2@example.com",
            first_name="User2",
        )

        self.client.force_authenticate(user=self.user1)

    def test_user_only_sees_own_categories_in_list(self):
        Category.objects.create(
            user=self.user1,
            name="Mine",
        )
        Category.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.get(
            reverse("category-list")
        )

        names = [
            category["name"]
            for category in response.data["results"]
        ]

        self.assertEqual(names, ["Mine"])

    def test_user_only_sees_own_saved_items_in_list(self):
        SavedItem.objects.create(
            user=self.user1,
            name="Mine",
        )
        SavedItem.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.get(
            reverse("saved-item-list")
        )

        names = [
            item["name"]
            for item in response.data["results"]
        ]

        self.assertEqual(names, ["Mine"])

    def test_retrieve_other_users_category_returns_404(self):
        category = Category.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.get(
            reverse("category-detail", args=[category.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_update_other_users_category_returns_404(self):
        category = Category.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.patch(
            reverse("category-detail", args=[category.id]),
            {"name": "Hacked"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        category.refresh_from_db()

        self.assertEqual(category.name, "Theirs")

    def test_delete_other_users_category_returns_404(self):
        category = Category.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.delete(
            reverse("category-detail", args=[category.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            Category.objects.filter(id=category.id).exists()
        )

    def test_retrieve_other_users_saved_item_returns_404(self):
        item = SavedItem.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.get(
            reverse("saved-item-detail", args=[item.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_update_other_users_saved_item_returns_404(self):
        item = SavedItem.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.patch(
            reverse("saved-item-detail", args=[item.id]),
            {"name": "Hacked"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        item.refresh_from_db()

        self.assertEqual(item.name, "Theirs")

    def test_delete_other_users_saved_item_returns_404(self):
        item = SavedItem.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.delete(
            reverse("saved-item-detail", args=[item.id])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            SavedItem.objects.filter(id=item.id).exists()
        )

    def test_cannot_attach_other_users_category_to_saved_item(self):
        other_category = Category.objects.create(
            user=self.user2,
            name="Theirs",
        )

        response = self.client.post(
            reverse("saved-item-list"),
            {
                "name": "Test",
                "categories": [
                    {
                        "category": other_category.id,
                        "priority": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertFalse(
            SavedItem.objects.filter(name="Test").exists()
        )


class PayloadOverrideProtectionTests(APITestCase):
    def setUp(self):
        self.user1 = create_user("user1@example.com")
        self.user2 = create_user("user2@example.com")

        self.client.force_authenticate(user=self.user1)

        self.list_url = reverse("saved-item-list")

    def test_user_field_in_payload_is_ignored_on_create(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Test",
                "user": self.user2.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        item = SavedItem.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(item.user, self.user1)

    def test_user_field_cannot_be_changed_on_update(self):
        item = SavedItem.objects.create(
            user=self.user1,
            name="Test",
        )

        response = self.client.patch(
            reverse("saved-item-detail", args=[item.id]),
            {"user": self.user2.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item.refresh_from_db()

        self.assertEqual(item.user, self.user1)

    def test_extracted_content_is_read_only_on_create(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Test",
                "extracted_content": {
                    "title": "hack",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        item = SavedItem.objects.get(
            id=response.data["id"]
        )

        self.assertIsNone(item.extracted_content)

    def test_metadata_is_read_only_on_create(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Test",
                "metadata": {
                    "foo": "hack",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        item = SavedItem.objects.get(
            id=response.data["id"]
        )

        self.assertIsNone(item.metadata)

    def test_extracted_content_is_read_only_on_update(self):
        item = SavedItem.objects.create(
            user=self.user1,
            name="Test",
        )

        response = self.client.patch(
            reverse("saved-item-detail", args=[item.id]),
            {
                "extracted_content": {
                    "title": "hack",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item.refresh_from_db()

        self.assertIsNone(item.extracted_content)

    def test_metadata_is_read_only_on_update(self):
        item = SavedItem.objects.create(
            user=self.user1,
            name="Test",
        )

        response = self.client.patch(
            reverse("saved-item-detail", args=[item.id]),
            {
                "metadata": {
                    "foo": "hack",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item.refresh_from_db()

        self.assertIsNone(item.metadata)


class SavedItemPaginationTests(APITestCase):
    def setUp(self):
        self.user = create_user("user@example.com")
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("saved-item-list")

        for index in range(25):
            SavedItem.objects.create(
                user=self.user,
                name=f"Item {index:02d}",
            )

    def test_default_page_size_is_20(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)

    def test_second_page_contains_remaining_items(self):
        response = self.client.get(
            self.list_url,
            {"page": 2},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNotNone(response.data["previous"])
        self.assertIsNone(response.data["next"])

    def test_custom_page_size(self):
        response = self.client.get(
            self.list_url,
            {"page_size": 10},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 10)

    def test_page_size_cannot_exceed_100(self):
        SavedItem.objects.all().delete()

        for index in range(120):
            SavedItem.objects.create(
                user=self.user,
                name=f"Item {index:03d}",
            )

        response = self.client.get(
            self.list_url,
            {"page_size": 1000},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 120)
        self.assertEqual(len(response.data["results"]), 100)

    def test_pagination_respects_ownership(self):
        other_user = create_user(
            "other@example.com",
            first_name="Other",
        )

        SavedItem.objects.all().delete()

        for index in range(25):
            SavedItem.objects.create(
                user=self.user,
                name=f"Mine {index:02d}",
            )

        for index in range(10):
            SavedItem.objects.create(
                user=other_user,
                name=f"Theirs {index:02d}",
            )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)

        returned_names = [
            item["name"]
            for item in response.data["results"]
        ]

        self.assertTrue(
            all(name.startswith("Mine") for name in returned_names)
        )


class SavedItemFilterTests(APITestCase):
    def setUp(self):
        self.user = create_user("user@example.com")
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("saved-item-list")

        self.games = Category.objects.create(
            user=self.user,
            name="Games",
        )

        self.programming = Category.objects.create(
            user=self.user,
            name="Programming",
        )

        now = timezone.now()

        self.completed_old = SavedItem.objects.create(
            user=self.user,
            name="Old Game",
            url="https://example.com/old-game",
            source="web",
            status=SavedItem.Status.COMPLETED,
            completed_at=now - timedelta(days=10),
            created_at=now - timedelta(days=10),
        )

        self.completed_recent = SavedItem.objects.create(
            user=self.user,
            name="Recent Game",
            url="https://youtube.com/recent-game",
            source="youtube",
            status=SavedItem.Status.COMPLETED,
            completed_at=now - timedelta(days=2),
            created_at=now - timedelta(days=2),
        )

        self.todo_programming = SavedItem.objects.create(
            user=self.user,
            name="Django Tutorial",
            url="https://example.com/django",
            source="web",
            status=SavedItem.Status.TO_DO,
            created_at=now - timedelta(days=5),
        )

        self.todo_reddit = SavedItem.objects.create(
            user=self.user,
            name="Python Reddit Post",
            url="https://reddit.com/python",
            source="reddit",
            status=SavedItem.Status.COMPLETED,
            created_at=now - timedelta(days=1),
        )

        self.completed_old.category_links.create(
            category=self.games,
            priority=1,
        )

        self.completed_recent.category_links.create(
            category=self.games,
            priority=1,
        )

        self.todo_programming.category_links.create(
            category=self.programming,
            priority=1,
        )

    def get_names(self, response):
        return {
            item["name"]
            for item in response.data["results"]
        }

    def test_filter_by_status(self):
        response = self.client.get(
            self.list_url,
            {"status": SavedItem.Status.COMPLETED},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            self.get_names(response),
            {"Old Game", "Recent Game"},
        )

    def test_filter_by_source(self):
        response = self.client.get(
            self.list_url,
            {"source": "youtube"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.get_names(response),
            {"Recent Game"},
        )

    def test_filter_by_category(self):
        response = self.client.get(
            self.list_url,
            {"category": self.games.id},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            self.get_names(response),
            {"Old Game", "Recent Game"},
        )

    def test_filter_by_created_after(self):
        cutoff = timezone.now() - timedelta(days=6)

        response = self.client.get(
            self.list_url,
            {
                "created_after": cutoff.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        names = self.get_names(response)

        self.assertEqual(
            names,
            {
                "Recent Game",
                "Django Tutorial",
                "Python Reddit Post",
            },
        )

    def test_filter_by_created_before(self):
        cutoff = timezone.now() - timedelta(days=6)

        response = self.client.get(
            self.list_url,
            {
                "created_before": cutoff.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        names = self.get_names(response)

        self.assertEqual(
            names,
            {"Old Game"},
        )

    def test_filter_by_completed_after(self):
        cutoff = timezone.now() - timedelta(days=5)

        response = self.client.get(
            self.list_url,
            {
                "completed_after": cutoff.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        names = self.get_names(response)

        self.assertEqual(
            names,
            {"Recent Game"},
        )

    def test_filter_by_completed_before(self):
        cutoff = timezone.now() - timedelta(days=5)

        response = self.client.get(
            self.list_url,
            {
                "completed_before": cutoff.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        names = self.get_names(response)

        self.assertEqual(
            names,
            {"Old Game"},
        )

    def test_filter_combines_multiple_filters(self):
        response = self.client.get(
            self.list_url,
            {
                "status": SavedItem.Status.COMPLETED,
                "source": "youtube",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.get_names(response),
            {"Recent Game"},
        )

    def test_filter_by_other_users_category_returns_empty(self):
        other_user = create_user(
            "other@example.com",
            first_name="Other",
        )

        other_category = Category.objects.create(
            user=other_user,
            name="Other",
        )

        SavedItem.objects.create(
            user=other_user,
            name="Other Item",
        )

        response = self.client.get(
            self.list_url,
            {"category": other_category.id},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])


class SavedItemSearchTests(APITestCase):
    def setUp(self):
        self.user = create_user("user@example.com")
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("saved-item-list")

        SavedItem.objects.create(
            user=self.user,
            name="Django REST Framework",
            url="https://example.com/drf",
            source="web",
        )

        SavedItem.objects.create(
            user=self.user,
            name="Python Tutorial",
            url="https://youtube.com/python",
            source="youtube",
        )

        SavedItem.objects.create(
            user=self.user,
            name="Gaming News",
            url="https://reddit.com/gaming",
            source="reddit",
        )

    def get_names(self, response):
        return {
            item["name"]
            for item in response.data["results"]
        }

    def test_search_by_name(self):
        response = self.client.get(
            self.list_url,
            {"search": "Django"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.get_names(response),
            {"Django REST Framework"},
        )

    def test_search_by_url(self):
        response = self.client.get(
            self.list_url,
            {"search": "youtube.com"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.get_names(response),
            {"Python Tutorial"},
        )

    def test_search_by_source(self):
        response = self.client.get(
            self.list_url,
            {"search": "reddit"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.get_names(response),
            {"Gaming News"},
        )

    def test_search_returns_empty_for_no_match(self):
        response = self.client.get(
            self.list_url,
            {"search": "does-not-exist"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_search_respects_ownership(self):
        other_user = create_user(
            "other@example.com",
            first_name="Other",
        )

        SavedItem.objects.create(
            user=other_user,
            name="Secret Django Content",
            url="https://example.com/secret",
            source="web",
        )

        response = self.client.get(
            self.list_url,
            {"search": "Django"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        names = self.get_names(response)

        self.assertEqual(
            names,
            {"Django REST Framework"},
        )


class SavedItemFilterTests(APITestCase):
    def setUp(self):
        self.user = create_user("user@example.com")
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("saved-item-list")

        self.games = Category.objects.create(
            user=self.user,
            name="Games",
        )

        self.programming = Category.objects.create(
            user=self.user,
            name="Programming",
        )

        now = timezone.now()

        self.completed_old = SavedItem.objects.create(
            user=self.user,
            name="Old Game",
            url="https://example.com/old-game",
            source="web",
            status=SavedItem.Status.COMPLETED,
            completed_at=now - timedelta(days=10),
        )

        self.completed_recent = SavedItem.objects.create(
            user=self.user,
            name="Recent Game",
            url="https://youtube.com/recent-game",
            source="youtube",
            status=SavedItem.Status.COMPLETED,
            completed_at=now - timedelta(days=2),
        )

        self.todo_programming = SavedItem.objects.create(
            user=self.user,
            name="Django Tutorial",
            url="https://example.com/django",
            source="web",
            status=SavedItem.Status.TO_DO,
        )

        self.todo_reddit = SavedItem.objects.create(
            user=self.user,
            name="Python Reddit Post",
            url="https://reddit.com/python",
            source="reddit",
            status=SavedItem.Status.TO_DO,
        )

        # auto_now_add ignores manually supplied created_at during create().
        # Set deterministic timestamps explicitly after creation.
        SavedItem.objects.filter(
            pk=self.completed_old.pk
        ).update(
            created_at=now - timedelta(days=10)
        )

        SavedItem.objects.filter(
            pk=self.completed_recent.pk
        ).update(
            created_at=now - timedelta(days=2)
        )

        SavedItem.objects.filter(
            pk=self.todo_programming.pk
        ).update(
            created_at=now - timedelta(days=5)
        )

        SavedItem.objects.filter(
            pk=self.todo_reddit.pk
        ).update(
            created_at=now - timedelta(days=1)
        )

        self.completed_old.category_links.create(
            category=self.games,
            priority=1,
        )

        self.completed_recent.category_links.create(
            category=self.games,
            priority=1,
        )

        self.todo_programming.category_links.create(
            category=self.programming,
            priority=1,
        )

    def get_names(self, response):
        return {
            item["name"]
            for item in response.data["results"]
        }

class SavedItemCombinedQueryTests(APITestCase):
    def setUp(self):
        self.user = create_user("user@example.com")
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("saved-item-list")

        self.games = Category.objects.create(
            user=self.user,
            name="Games",
        )

        now = timezone.now()

        for index in range(15):
            item = SavedItem.objects.create(
                user=self.user,
                name=f"Game Article {index:02d}",
                url=f"https://example.com/game-{index}",
                source="web",
                status=SavedItem.Status.COMPLETED,
                completed_at=now - timedelta(days=index),
                created_at=now - timedelta(days=index),
            )

            item.category_links.create(
                category=self.games,
                priority=1,
            )

        for index in range(5):
            SavedItem.objects.create(
                user=self.user,
                name=f"Other Content {index:02d}",
                source="reddit",
                status=SavedItem.Status.COMPLETED,
                completed_at=now - timedelta(days=index),
                created_at=now - timedelta(days=index),
            )

    def test_filter_search_ordering_and_pagination_work_together(self):
        response = self.client.get(
            self.list_url,
            {
                "status": SavedItem.Status.COMPLETED,
                "category": self.games.id,
                "search": "Game",
                "ordering": "name",
                "page_size": 5,
                "page": 1,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 15)
        self.assertEqual(len(response.data["results"]), 5)

        names = [
            item["name"]
            for item in response.data["results"]
        ]

        self.assertEqual(
            names,
            [
                "Game Article 00",
                "Game Article 01",
                "Game Article 02",
                "Game Article 03",
                "Game Article 04",
            ],
        )

    def test_combined_query_second_page(self):
        response = self.client.get(
            self.list_url,
            {
                "status": SavedItem.Status.COMPLETED,
                "category": self.games.id,
                "search": "Game",
                "ordering": "name",
                "page_size": 5,
                "page": 2,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data["count"], 15)
        self.assertEqual(len(response.data["results"]), 5)

        names = [
            item["name"]
            for item in response.data["results"]
        ]

        self.assertEqual(
            names,
            [
                "Game Article 05",
                "Game Article 06",
                "Game Article 07",
                "Game Article 08",
                "Game Article 09",
            ],
        )

    def test_combined_query_does_not_leak_other_users_items(self):
        other_user = create_user(
            "other@example.com",
            first_name="Other",
        )

        other_category = Category.objects.create(
            user=other_user,
            name="Games",
        )

        other_item = SavedItem.objects.create(
            user=other_user,
            name="Game Article Secret",
            source="web",
            status=SavedItem.Status.COMPLETED,
            completed_at=timezone.now(),
        )

        other_item.category_links.create(
            category=other_category,
            priority=1,
        )

        response = self.client.get(
            self.list_url,
            {
                "status": SavedItem.Status.COMPLETED,
                "search": "Game",
                "ordering": "name",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        names = {
            item["name"]
            for item in response.data["results"]
        }

        self.assertNotIn(
            "Game Article Secret",
            names,
        )

        self.assertEqual(
            response.data["count"],
            15,
        )

