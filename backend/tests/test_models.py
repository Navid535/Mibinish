from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.saved_items.models import Category, SavedItem, SavedItemCategory

User = get_user_model()

class CustomUserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
        email="john@example.com",
        password="secret123",
        first_name="John",
        )
        self.assertEqual(user.email, "john@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_password_is_hashed(self):
        raw_password = "secret123"

        user = User.objects.create_user(
            email="john@example.com",
            password=raw_password,
            first_name="John",
        )

        self.assertNotEqual(user.password, raw_password)
        self.assertTrue(user.check_password(raw_password))

    def test_default_plan_is_free(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="secret123",
            first_name="John",
        )

        self.assertEqual(user.plan, "FR")

    def test_default_completed_items_retention_days_is_seven(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="secret123",
            first_name="John",
        )

        self.assertEqual(user.completed_items_retention_days, 7)

    def test_full_name_with_first_and_last_name(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="secret123",
            first_name=" John ",
            last_name=" Doe ",
        )

        self.assertEqual(user.full_name, "John Doe")

    def test_full_name_without_last_name(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="secret123",
            first_name=" John ",
        )

        self.assertEqual(user.full_name, "John")

    def test_str_returns_full_name(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="secret123",
            first_name="John",
            last_name="Doe",
        )

        self.assertEqual(str(user), "John Doe")

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="",
                password="secret123",
                first_name="John",
            )

    def test_create_user_requires_first_name(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="john@example.com",
                password="secret123",
            )

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="secret123",
            first_name="Admin",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_email_is_unique(self):
        User.objects.create_user(
            email="john@example.com",
            password="secret123",
            first_name="John",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="john@example.com",
                    password="another123",
                    first_name="Another",
                )

class CategoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
        email="[user@example.com](mailto:user@example.com)",
        password="secret123",
        first_name="John",
        )
        self.other_user = User.objects.create_user(
        email="[other@example.com](mailto:other@example.com)",
        password="secret123",
        first_name="Jane",
        )


    def test_create_category(self):
        category = Category.objects.create(
            user=self.user,
            name="Games",
        )

        self.assertEqual(category.user, self.user)
        self.assertEqual(category.name, "Games")

    def test_user_categories_related_name(self):
        category = Category.objects.create(
            user=self.user,
            name="Games",
        )

        self.assertIn(category, self.user.categories.all())

    def test_default_color(self):
        category = Category.objects.create(
            user=self.user,
            name="Games",
        )

        self.assertEqual(category.color, "#3299a8")

    def test_str_returns_name(self):
        category = Category.objects.create(
            user=self.user,
            name="Games",
        )

        self.assertEqual(str(category), "Games")

    def test_visible_to_returns_only_user_categories(self):
        user_category = Category.objects.create(
            user=self.user,
            name="Games",
        )
        other_category = Category.objects.create(
            user=self.other_user,
            name="Movies",
        )

        queryset = Category.objects.visible_to(self.user)

        self.assertIn(user_category, queryset)
        self.assertNotIn(other_category, queryset)

    def test_visible_to_other_user_does_not_expose_categories(self):
        Category.objects.create(
            user=self.user,
            name="Games",
        )

        queryset = Category.objects.visible_to(self.other_user)

        self.assertEqual(queryset.count(), 0)

    def test_visible_to_none_returns_empty_queryset(self):
        Category.objects.create(
            user=self.user,
            name="Games",
        )

        queryset = Category.objects.visible_to(None)

        self.assertEqual(queryset.count(), 0)

    def test_visible_to_anonymous_user_returns_empty_queryset(self):
        Category.objects.create(
            user=self.user,
            name="Games",
        )

        queryset = Category.objects.visible_to(AnonymousUser())

        self.assertEqual(queryset.count(), 0)

    def test_name_is_required(self):
        category = Category(
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_ordering_is_by_name(self):
        category_z = Category.objects.create(
            user=self.user,
            name="Zebra",
        )
        category_a = Category.objects.create(
            user=self.user,
            name="Articles",
        )

        categories = list(Category.objects.all())

        self.assertEqual(categories, [category_a, category_z])

    def test_category_name_is_unique_per_user(self):
        Category.objects.create(
            user=self.user,
            name="Games",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(
                    user=self.user,
                    name="Games",
                )

    def test_same_category_name_is_allowed_for_different_users(self):
        first_category = Category.objects.create(
            user=self.user,
            name="Games",
        )
        second_category = Category.objects.create(
            user=self.other_user,
            name="Games",
        )

        self.assertNotEqual(first_category.user, second_category.user)
        self.assertEqual(first_category.name, second_category.name)

    def test_deleting_user_deletes_categories(self):
        category = Category.objects.create(
            user=self.user,
            name="Games",
        )

        category_id = category.pk
        self.user.delete()

        self.assertFalse(Category.objects.filter(pk=category_id).exists())

class SavedItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
        email="[user@example.com](mailto:user@example.com)",
        password="secret123",
        first_name="John",
        )
        self.other_user = User.objects.create_user(
        email="[other@example.com](mailto:other@example.com)",
        password="secret123",
        first_name="Jane",
        )

    def create_saved_item(self, **kwargs):
        defaults = {
            "user": self.user,
            "name": "Django Documentation",
            "url": "https://docs.djangoproject.com/",
        }
        defaults.update(kwargs)
        return SavedItem.objects.create(**defaults)

    def test_create_saved_item(self):
        item = self.create_saved_item()

        self.assertEqual(item.user, self.user)
        self.assertEqual(item.name, "Django Documentation")
        self.assertEqual(item.url, "https://docs.djangoproject.com/")

    def test_default_status_is_to_do(self):
        item = self.create_saved_item()

        self.assertEqual(item.status, SavedItem.Status.TO_DO)

    def test_source_defaults_to_empty_string(self):
        item = self.create_saved_item()

        self.assertEqual(item.source, "")

    def test_extracted_content_defaults_to_none(self):
        item = self.create_saved_item()

        self.assertIsNone(item.extracted_content)

    def test_metadata_defaults_to_none(self):
        item = self.create_saved_item()

        self.assertIsNone(item.metadata)

    def test_json_fields_store_structured_data(self):
        extracted_content = {
            "title": "Django",
            "author": "Django Software Foundation",
            "tags": ["django", "python"],
        }
        metadata = {
            "language": "en",
            "word_count": 1234,
        }

        item = self.create_saved_item(
            extracted_content=extracted_content,
            metadata=metadata,
        )

        item.refresh_from_db()

        self.assertEqual(item.extracted_content, extracted_content)
        self.assertEqual(item.metadata, metadata)

    def test_created_at_is_set(self):
        before = timezone.now()

        item = self.create_saved_item()

        after = timezone.now()

        self.assertIsNotNone(item.created_at)
        self.assertGreaterEqual(item.created_at, before)
        self.assertLessEqual(item.created_at, after)

    def test_updated_at_is_set(self):
        item = self.create_saved_item()

        self.assertIsNotNone(item.updated_at)

    def test_updated_at_changes_after_save(self):
        item = self.create_saved_item()
        old_updated_at = item.updated_at

        item.name = "Updated name"
        item.save()

        self.assertGreater(item.updated_at, old_updated_at)

    def test_visible_to_returns_only_user_items(self):
        user_item = self.create_saved_item(
            name="User item",
        )
        other_item = SavedItem.objects.create(
            user=self.other_user,
            name="Other item",
            url="https://example.com/",
        )

        queryset = SavedItem.objects.visible_to(self.user)

        self.assertIn(user_item, queryset)
        self.assertNotIn(other_item, queryset)

    def test_visible_to_other_user_does_not_expose_items(self):
        self.create_saved_item()

        queryset = SavedItem.objects.visible_to(self.other_user)

        self.assertEqual(queryset.count(), 0)

    def test_visible_to_none_returns_empty_queryset(self):
        self.create_saved_item()

        queryset = SavedItem.objects.visible_to(None)

        self.assertEqual(queryset.count(), 0)

    def test_visible_to_anonymous_user_returns_empty_queryset(self):
        self.create_saved_item()

        queryset = SavedItem.objects.visible_to(AnonymousUser())

        self.assertEqual(queryset.count(), 0)

    def test_name_only_is_valid(self):
        item = SavedItem.objects.create(
            user=self.user,
            name="Django Documentation",
            url=None,
        )

        self.assertEqual(item.name, "Django Documentation")
        self.assertIsNone(item.url)

    def test_url_only_is_valid(self):
        item = SavedItem.objects.create(
            user=self.user,
            name=None,
            url="https://docs.djangoproject.com/",
        )

        self.assertIsNone(item.name)
        self.assertEqual(item.url, "https://docs.djangoproject.com/")

    def test_name_and_url_are_both_valid(self):
        item = self.create_saved_item()

        self.assertIsNotNone(item.name)
        self.assertIsNotNone(item.url)

    def test_name_and_url_cannot_both_be_null(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedItem.objects.create(
                    user=self.user,
                    name=None,
                    url=None,
                )

    def test_todo_without_completed_at_is_valid(self):
        item = self.create_saved_item(
            status=SavedItem.Status.TO_DO,
            completed_at=None,
        )

        self.assertEqual(item.status, SavedItem.Status.TO_DO)
        self.assertIsNone(item.completed_at)

    def test_completed_with_completed_at_is_valid(self):
        completed_at = timezone.now()

        item = self.create_saved_item(
            status=SavedItem.Status.COMPLETED,
            completed_at=completed_at,
        )

        self.assertEqual(item.status, SavedItem.Status.COMPLETED)
        self.assertEqual(item.completed_at, completed_at)

    def test_todo_with_completed_at_is_invalid(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedItem.objects.create(
                    user=self.user,
                    name="Test item",
                    status=SavedItem.Status.TO_DO,
                    completed_at=timezone.now(),
                )

    def test_completed_without_completed_at_is_invalid(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedItem.objects.create(
                    user=self.user,
                    name="Test item",
                    status=SavedItem.Status.COMPLETED,
                    completed_at=None,
                )

    def test_str_returns_name_when_name_exists(self):
        item = self.create_saved_item(
            name="Django Documentation",
        )

        self.assertEqual(str(item), "Django Documentation")

    def test_saved_item_ordering(self):
        older_item = self.create_saved_item(
            name="Older",
        )

        newer_item = self.create_saved_item(
            name="Newer",
        )

        self.assertEqual(
            list(SavedItem.objects.all()),
            [newer_item, older_item],
        )

    def test_deleting_user_deletes_saved_items(self):
        item = self.create_saved_item()
        item_id = item.pk

        self.user.delete()

        self.assertFalse(SavedItem.objects.filter(pk=item_id).exists())

class SavedItemCategoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
        email="[user@example.com](mailto:user@example.com)",
        password="secret123",
        first_name="John",
        )

        self.category = Category.objects.create(
            user=self.user,
            name="Games",
        )

        self.saved_item = SavedItem.objects.create(
            user=self.user,
            name="Fallen Aces",
            url="https://example.com/fallen-aces",
        )

    def create_link(self, **kwargs):
        defaults = {
            "saved_item": self.saved_item,
            "category": self.category,
        }
        defaults.update(kwargs)
        return SavedItemCategory.objects.create(**defaults)

    def test_create_saved_item_category(self):
        link = self.create_link()

        self.assertEqual(link.saved_item, self.saved_item)
        self.assertEqual(link.category, self.category)

    def test_default_priority_is_one(self):
        link = self.create_link()

        self.assertEqual(link.priority, 1)

    def test_priority_one_is_valid(self):
        link = self.create_link(priority=1)

        self.assertEqual(link.priority, 1)

    def test_priority_greater_than_one_is_valid(self):
        link = self.create_link(priority=5)

        self.assertEqual(link.priority, 5)

    def test_priority_zero_is_invalid(self):
        link = SavedItemCategory(
            saved_item=self.saved_item,
            category=self.category,
            priority=0,
        )

        with self.assertRaises(ValidationError):
            link.full_clean()

    def test_negative_priority_is_invalid(self):
        link = SavedItemCategory(
            saved_item=self.saved_item,
            category=self.category,
            priority=-1,
        )

        with self.assertRaises(ValidationError):
            link.full_clean()

    def test_duplicate_saved_item_category_is_not_allowed(self):
        self.create_link()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_link()

    def test_saved_item_category_link_related_name(self):
        link = self.create_link()

        self.assertIn(link, self.saved_item.category_links.all())

    def test_category_item_links_related_name(self):
        link = self.create_link()

        self.assertIn(link, self.category.item_links.all())

    def test_saved_item_categories_relationship(self):
        self.create_link()

        self.assertIn(
            self.category,
            self.saved_item.categories.all(),
        )

    def test_category_saved_items_relationship(self):
        self.create_link()

        self.assertIn(
            self.saved_item,
            self.category.saved_items.all(),
        )

    def test_saved_item_can_belong_to_multiple_categories(self):
        second_category = Category.objects.create(
            user=self.user,
            name="Learn Later",
        )

        SavedItemCategory.objects.create(
            saved_item=self.saved_item,
            category=self.category,
            priority=1,
        )

        SavedItemCategory.objects.create(
            saved_item=self.saved_item,
            category=second_category,
            priority=1,
        )

        self.assertEqual(
            self.saved_item.categories.count(),
            2,
        )

    def test_category_can_contain_multiple_saved_items(self):
        second_item = SavedItem.objects.create(
            user=self.user,
            name="Another game",
            url="https://example.com/another-game",
        )

        SavedItemCategory.objects.create(
            saved_item=self.saved_item,
            category=self.category,
            priority=1,
        )

        SavedItemCategory.objects.create(
            saved_item=second_item,
            category=self.category,
            priority=1,
        )

        self.assertEqual(
            self.category.saved_items.count(),
            2,
        )

    def test_same_priority_is_allowed_for_multiple_items(self):
        second_item = SavedItem.objects.create(
            user=self.user,
            name="Another game",
            url="https://example.com/another-game",
        )

        first_link = SavedItemCategory.objects.create(
            saved_item=self.saved_item,
            category=self.category,
            priority=1,
        )

        second_link = SavedItemCategory.objects.create(
            saved_item=second_item,
            category=self.category,
            priority=1,
        )

        self.assertEqual(first_link.priority, second_link.priority)

    def test_deleting_category_deletes_links(self):
        link = self.create_link()
        link_id = link.pk

        self.category.delete()

        self.assertFalse(
            SavedItemCategory.objects.filter(pk=link_id).exists()
        )

    def test_deleting_saved_item_deletes_links(self):
        link = self.create_link()
        link_id = link.pk

        self.saved_item.delete()

        self.assertFalse(
            SavedItemCategory.objects.filter(pk=link_id).exists()
        )

    def test_saved_item_category_str(self):
        link = self.create_link()

        self.assertEqual(
            str(link),
            "Fallen Aces → Games",
        )

    def test_cross_user_saved_item_category_is_currently_not_enforced(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="secret123",
            first_name="Jane",
        )

        other_category = Category.objects.create(
            user=other_user,
            name="Other",
        )

        # The current models do not implement a cross-table ownership
        # constraint. ForeignKey constraints alone allow this relation.
        link = SavedItemCategory.objects.create(
            saved_item=self.saved_item,
            category=other_category,
        )

        self.assertEqual(link.saved_item.user, self.user)
        self.assertEqual(link.category.user, other_user)
        self.assertNotEqual(
            link.saved_item.user,
            link.category.user,
        )

