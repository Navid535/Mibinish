from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.saved_items.models import Category, SavedItem
from apps.users.models import CustomUser


def create_user(email, first_name="Test"):
    return CustomUser.objects.create_user(
        email=email, password="strong-pass-123", first_name=first_name,
    )


class CategoryCRUDTests(APITestCase):
    def setUp(self):
        self.user = create_user("user1@example.com")
        self.client.force_authenticate(user=self.user)

    def test_create_category(self):
        response = self.client.post(
            reverse('category-list'), {"name": "Games", "color": "#ff0000"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(Category.objects.first().user, self.user)

    def test_list_categories(self):
        Category.objects.create(user=self.user, name="A")
        Category.objects.create(user=self.user, name="B")
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_category(self):
        category = Category.objects.create(user=self.user, name="A")
        response = self.client.get(reverse('category-detail', args=[category.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "A")

    def test_update_category(self):
        category = Category.objects.create(user=self.user, name="A")
        response = self.client.patch(
            reverse('category-detail', args=[category.id]), {"name": "B"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.name, "B")

    def test_delete_category(self):
        category = Category.objects.create(user=self.user, name="A")
        response = self.client.delete(reverse('category-detail', args=[category.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=category.id).exists())


class SavedItemCRUDTests(APITestCase):
    def setUp(self):
        self.user = create_user("user1@example.com")
        self.client.force_authenticate(user=self.user)

    def test_create_saved_item_with_name(self):
        response = self.client.post(reverse('saved-item-list'), {"name": "Article"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SavedItem.objects.count(), 1)

    def test_create_saved_item_without_name_or_url_fails(self):
        response = self.client.post(reverse('saved-item-list'), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_saved_items(self):
        SavedItem.objects.create(user=self.user, name="A")
        SavedItem.objects.create(user=self.user, name="B")
        response = self.client.get(reverse('saved-item-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_saved_item(self):
        item = SavedItem.objects.create(user=self.user, name="A")
        response = self.client.get(reverse('saved-item-detail', args=[item.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "A")

    def test_update_saved_item(self):
        item = SavedItem.objects.create(user=self.user, name="A")
        response = self.client.patch(
            reverse('saved-item-detail', args=[item.id]), {"name": "B"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.name, "B")

    def test_delete_saved_item(self):
        item = SavedItem.objects.create(user=self.user, name="A")
        response = self.client.delete(reverse('saved-item-detail', args=[item.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SavedItem.objects.filter(id=item.id).exists())


class UnauthenticatedAccessTests(APITestCase):
    def test_category_list_requires_auth(self):
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_category_create_requires_auth(self):
        response = self.client.post(reverse('category-list'), {"name": "A"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_saved_item_list_requires_auth(self):
        response = self.client.get(reverse('saved-item-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_saved_item_create_requires_auth(self):
        response = self.client.post(reverse('saved-item-list'), {"name": "A"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CrossUserOwnershipTests(APITestCase):
    def setUp(self):
        self.user1 = create_user("user1@example.com")
        self.user2 = create_user("user2@example.com")
        self.client.force_authenticate(user=self.user1)

    def test_user_only_sees_own_categories_in_list(self):
        Category.objects.create(user=self.user1, name="Mine")
        Category.objects.create(user=self.user2, name="Theirs")
        response = self.client.get(reverse('category-list'))
        names = [c['name'] for c in response.data]
        self.assertEqual(names, ["Mine"])

    def test_user_only_sees_own_saved_items_in_list(self):
        SavedItem.objects.create(user=self.user1, name="Mine")
        SavedItem.objects.create(user=self.user2, name="Theirs")
        response = self.client.get(reverse('saved-item-list'))
        names = [i['name'] for i in response.data]
        self.assertEqual(names, ["Mine"])

    def test_retrieve_other_users_category_returns_404(self):
        category = Category.objects.create(user=self.user2, name="Theirs")
        response = self.client.get(reverse('category-detail', args=[category.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_other_users_category_returns_404(self):
        category = Category.objects.create(user=self.user2, name="Theirs")
        response = self.client.patch(
            reverse('category-detail', args=[category.id]), {"name": "Hacked"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        category.refresh_from_db()
        self.assertEqual(category.name, "Theirs")

    def test_delete_other_users_category_returns_404(self):
        category = Category.objects.create(user=self.user2, name="Theirs")
        response = self.client.delete(reverse('category-detail', args=[category.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Category.objects.filter(id=category.id).exists())

    def test_retrieve_other_users_saved_item_returns_404(self):
        item = SavedItem.objects.create(user=self.user2, name="Theirs")
        response = self.client.get(reverse('saved-item-detail', args=[item.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_other_users_saved_item_returns_404(self):
        item = SavedItem.objects.create(user=self.user2, name="Theirs")
        response = self.client.patch(
            reverse('saved-item-detail', args=[item.id]), {"name": "Hacked"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        item.refresh_from_db()
        self.assertEqual(item.name, "Theirs")

    def test_delete_other_users_saved_item_returns_404(self):
        item = SavedItem.objects.create(user=self.user2, name="Theirs")
        response = self.client.delete(reverse('saved-item-detail', args=[item.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(SavedItem.objects.filter(id=item.id).exists())

    def test_cannot_attach_other_users_category_to_saved_item(self):
        other_category = Category.objects.create(user=self.user2, name="Theirs")
        response = self.client.post(
            reverse('saved-item-list'),
            {"name": "Test", "categories": [{"category": other_category.id, "priority": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SavedItem.objects.filter(name="Test").exists())


class PayloadOverrideProtectionTests(APITestCase):
    def setUp(self):
        self.user1 = create_user("user1@example.com")
        self.user2 = create_user("user2@example.com")
        self.client.force_authenticate(user=self.user1)

    def test_user_field_in_payload_ignored_on_create(self):
        response = self.client.post(
            reverse('saved-item-list'),
            {"name": "Test", "user": self.user2.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = SavedItem.objects.get(id=response.data['id'])
        self.assertEqual(item.user, self.user1)

    def test_user_field_cannot_be_changed_on_update(self):
        item = SavedItem.objects.create(user=self.user1, name="Test")
        response = self.client.patch(
            reverse('saved-item-detail', args=[item.id]),
            {"user": self.user2.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.user, self.user1)

    def test_extracted_content_ignored_on_create(self):
        response = self.client.post(
            reverse('saved-item-list'),
            {"name": "Test", "extracted_content": {"title": "hack"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = SavedItem.objects.get(id=response.data['id'])
        self.assertIsNone(item.extracted_content)

    def test_metadata_ignored_on_create(self):
        response = self.client.post(
            reverse('saved-item-list'),
            {"name": "Test", "metadata": {"foo": "hack"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = SavedItem.objects.get(id=response.data['id'])
        self.assertIsNone(item.metadata)

    def test_extracted_content_ignored_on_update(self):
        item = SavedItem.objects.create(user=self.user1, name="Test")
        response = self.client.patch(
            reverse('saved-item-detail', args=[item.id]),
            {"extracted_content": {"title": "hack"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertIsNone(item.extracted_content)

    def test_metadata_ignored_on_update(self):
        item = SavedItem.objects.create(user=self.user1, name="Test")
        response = self.client.patch(
            reverse('saved-item-detail', args=[item.id]),
            {"metadata": {"foo": "hack"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertIsNone(item.metadata)