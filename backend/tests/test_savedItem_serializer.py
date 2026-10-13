from django.test import TestCase

from apps.saved_items import services
from apps.saved_items.models import Category, SavedItem
from apps.saved_items.serializers import CategorySerializer, SavedItemSerializer
from apps.users.models import CustomUser


def create_user(email, first_name="Test"):
    return CustomUser.objects.create_user(
        email=email,
        password="strong-pass-123",
        first_name=first_name,
    )


class DummyRequest:
    def __init__(self, user):
        self.user = user


class CategorySerializerTests(TestCase):
    def setUp(self):
        self.user1 = create_user("user1@example.com")
        self.user2 = create_user("user2@example.com")

    def test_create_category(self):
        serializer = CategorySerializer(
            data={"name": "Games", "color": "#ff0000"},
            context={"request": DummyRequest(self.user1)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        category = serializer.save()
        self.assertEqual(category.user, self.user1)
        self.assertEqual(category.name, "Games")

    def test_duplicate_category_name_same_user_fails(self):
        Category.objects.create(user=self.user1, name="Games")
        serializer = CategorySerializer(
            data={"name": "Games"},
            context={"request": DummyRequest(self.user1)},
        )
        self.assertFalse(serializer.is_valid())

    def test_same_category_name_different_users_allowed(self):
        Category.objects.create(user=self.user1, name="Games")
        serializer = CategorySerializer(
            data={"name": "Games"},
            context={"request": DummyRequest(self.user2)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        category = serializer.save()
        self.assertEqual(category.user, self.user2)


class SavedItemSerializerValidationTests(TestCase):
    def setUp(self):
        self.user1 = create_user("user1@example.com")
        self.user2 = create_user("user2@example.com")
        self.context1 = {"request": DummyRequest(self.user1)}

    def test_missing_name_and_url_fails(self):
        serializer = SavedItemSerializer(data={}, context=self.context1)
        self.assertFalse(serializer.is_valid())

    def test_only_name_passes(self):
        serializer = SavedItemSerializer(
            data={"name": "Some item"},
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()
        self.assertEqual(item.name, "Some item")
        self.assertIsNone(item.url)

    def test_only_url_passes(self):
        serializer = SavedItemSerializer(
            data={"url": "https://example.com"},
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()
        self.assertEqual(item.url, "https://example.com")
        self.assertIsNone(item.name)

    def test_user_cannot_be_overridden_via_payload(self):
        serializer = SavedItemSerializer(
            data={"name": "Test", "user": self.user2.id},
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()
        self.assertEqual(item.user, self.user1)  # نه user2

    def test_extracted_content_not_writable(self):
        serializer = SavedItemSerializer(
            data={"name": "Test", "extracted_content": {"title": "hack"}},
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()
        self.assertIsNone(item.extracted_content)

    def test_metadata_not_writable(self):
        serializer = SavedItemSerializer(
            data={"name": "Test", "metadata": {"foo": "hack"}},
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()
        self.assertIsNone(item.metadata)

    def test_category_from_other_user_rejected(self):
        other_category = Category.objects.create(user=self.user2, name="Games")
        serializer = SavedItemSerializer(
            data={
                "name": "Test",
                "categories": [{"category": other_category.id, "priority": 1}],
            },
            context=self.context1,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("categories", serializer.errors)

    def test_duplicate_category_in_same_saved_item_rejected(self):
        category = Category.objects.create(user=self.user1, name="Games")
        serializer = SavedItemSerializer(
            data={
                "name": "Test",
                "categories": [
                    {"category": category.id, "priority": 1},
                    {"category": category.id, "priority": 2},
                ],
            },
            context=self.context1,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("categories", serializer.errors)

    def test_priority_zero_rejected(self):
        category = Category.objects.create(user=self.user1, name="Games")
        serializer = SavedItemSerializer(
            data={
                "name": "Test",
                "categories": [{"category": category.id, "priority": 0}],
            },
            context=self.context1,
        )
        self.assertFalse(serializer.is_valid())

    def test_priority_negative_rejected(self):
        category = Category.objects.create(user=self.user1, name="Games")
        serializer = SavedItemSerializer(
            data={
                "name": "Test",
                "categories": [{"category": category.id, "priority": -1}],
            },
            context=self.context1,
        )
        self.assertFalse(serializer.is_valid())


class SavedItemSerializerStatusTests(TestCase):
    def setUp(self):
        self.user1 = create_user("user1@example.com")
        self.context1 = {"request": DummyRequest(self.user1)}

    def test_create_with_status_completed_sets_completed_at(self):
        serializer = SavedItemSerializer(
            data={"name": "Test", "status": SavedItem.Status.COMPLETED},
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        item = serializer.save()
        self.assertIsNotNone(item.completed_at)

    def test_update_to_do_to_completed_sets_completed_at(self):
        item = services.create_saved_item(user=self.user1, name="Test")
        self.assertIsNone(item.completed_at)

        serializer = SavedItemSerializer(
            item,
            data={"status": SavedItem.Status.COMPLETED},
            partial=True,
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertIsNotNone(updated.completed_at)

    def test_update_completed_to_to_do_clears_completed_at(self):
        item = services.create_saved_item(
            user=self.user1,
            name="Test",
            status=SavedItem.Status.COMPLETED,
        )
        self.assertIsNotNone(item.completed_at)

        serializer = SavedItemSerializer(
            item,
            data={"status": SavedItem.Status.TO_DO},
            partial=True,
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertIsNone(updated.completed_at)


class SavedItemSerializerCategorySyncTests(TestCase):
    def setUp(self):
        self.user1 = create_user("user1@example.com")
        self.context1 = {"request": DummyRequest(self.user1)}
        self.cat_a = Category.objects.create(user=self.user1, name="A")
        self.cat_b = Category.objects.create(user=self.user1, name="B")

    def test_update_without_categories_keeps_existing(self):
        item = services.create_saved_item(
            user=self.user1,
            name="Test",
            category_links=[{"category": self.cat_a, "priority": 1}],
        )
        self.assertEqual(item.category_links.count(), 1)

        serializer = SavedItemSerializer(
            item,
            data={"name": "Updated"},
            partial=True,
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.category_links.count(), 1)
        self.assertEqual(updated.category_links.first().category, self.cat_a)

    def test_update_with_empty_categories_removes_all(self):
        item = services.create_saved_item(
            user=self.user1,
            name="Test",
            category_links=[{"category": self.cat_a, "priority": 1}],
        )
        serializer = SavedItemSerializer(
            item,
            data={"categories": []},
            partial=True,
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.category_links.count(), 0)

    def test_update_with_new_categories_syncs(self):
        item = services.create_saved_item(
            user=self.user1,
            name="Test",
            category_links=[{"category": self.cat_a, "priority": 1}],
        )
        serializer = SavedItemSerializer(
            item,
            data={"categories": [{"category": self.cat_b.id, "priority": 2}]},
            partial=True,
            context=self.context1,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        links = list(updated.category_links.all())
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].category, self.cat_b)
        self.assertEqual(links[0].priority, 2)


class SavedItemOwnershipGapTests(TestCase):
    def test_service_layer_does_not_enforce_ownership_by_itself(self):
        owner = create_user("owner@example.com")
        item = services.create_saved_item(user=owner, name="Owner's item")
        updated = services.update_saved_item(saved_item=item, name="Changed by anyone")
        self.assertEqual(updated.name, "Changed by anyone")
