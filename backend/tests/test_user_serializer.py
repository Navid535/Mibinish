from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.users.models import CustomUser
from apps.users.serializers import (
    ChangePasswordSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterSerializerTests(TestCase):
    def test_valid_data(self):
        data = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "password": "secret123terces",
        }

        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_creates_user(self):
        data = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "password": "secret123terces",
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(user.email, "john@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")

    def test_password_is_hashed(self):
        data = {
            "email": "john@example.com",
            "first_name": "John",
            "password": "secret123terces",
        }

        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertNotEqual(user.password, "secret123terces")
        self.assertTrue(user.check_password("secret123terces"))

    def test_password_is_write_only(self):
        data = {
            "email": "john@example.com",
            "first_name": "John",
            "password": "secret123terces",
        }

        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertNotIn("password", serializer.data)

    def test_email_is_required(self):
        data = {
            "first_name": "John",
            "password": "secret123terces",
        }

        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_first_name_is_required(self):
        data = {
            "email": "john@example.com",
            "password": "secret123terces",
        }

        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("first_name", serializer.errors)

    def test_password_minimum_length(self):
        data = {
            "email": "john@example.com",
            "first_name": "John",
            "password": "1234567",
        }

        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_duplicate_email_is_rejected(self):
        CustomUser.objects.create_user(
            email="john@example.com",
            first_name="John",
            password="secret123terces",
        )

        data = {
            "email": "john@example.com",
            "first_name": "Jane",
            "password": "secret123terces",
        }

        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class UserSerializerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            password="secret123terces",
        )

    def test_serializes_user(self):
        serializer = UserSerializer(self.user)

        self.assertEqual(
            serializer.data["email"],
            "john@example.com",
        )
        self.assertEqual(
            serializer.data["first_name"],
            "John",
        )
        self.assertEqual(
            serializer.data["last_name"],
            "Doe",
        )

    def test_password_is_not_serialized(self):
        serializer = UserSerializer(self.user)

        self.assertNotIn("password", serializer.data)

    def test_read_only_fields(self):
        serializer = UserSerializer(
            self.user,
            data={
                "email": "changed@example.com",
                "plan": "PR",
                "premium_until": "2030-01-01",
                "first_name": "Jane",
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.user.refresh_from_db()

        self.assertEqual(self.user.email, "john@example.com")
        self.assertEqual(self.user.plan, "FR")
        self.assertIsNone(self.user.premium_until)
        self.assertEqual(self.user.first_name, "Jane")


class ChangePasswordSerializerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="john@example.com",
            first_name="John",
            password="oldpassword123",
        )
        self.request = type(
            "Request",
            (),
            {"user": self.user},
        )()

    def test_changes_password(self):
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "oldpassword123",
                "new_password": "newpassword123",
            },
            context={"request": self.request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.user.refresh_from_db()

        self.assertTrue(self.user.check_password("newpassword123"))
        self.assertFalse(self.user.check_password("oldpassword123"))

    def test_rejects_wrong_old_password(self):
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "wrongpassword",
                "new_password": "newpassword123",
            },
            context={"request": self.request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("old_password", serializer.errors)

    def test_rejects_weak_new_password(self):
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "oldpassword123",
                "new_password": "123",
            },
            context={"request": self.request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)

    def test_free_user_cannot_change_retention_days(self):
        self.user.plan = "FR"
        self.user.premium_until = None
        self.user.save(update_fields=["plan", "premium_until"])
        serializer = UserSerializer(
            self.user,
            data={"completed_items_retention_days": 30},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "completed_items_retention_days",
            serializer.errors,
        )

    def test_active_premium_user_can_change_retention_days(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() + timedelta(days=30)
        self.user.save(update_fields=["plan", "premium_until"])
        serializer = UserSerializer(
            self.user,
            data={"completed_items_retention_days": 30},
            partial=True,
        )
        self.assertTrue(serializer.is_valid())

    def test_expired_premium_user_cannot_change_retention_days(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() - timedelta(days=1)
        self.user.save(update_fields=["plan", "premium_until"])
        serializer = UserSerializer(
            self.user,
            data={"completed_items_retention_days": 30},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "completed_items_retention_days",
            serializer.errors,
        )

    def test_retention_days_must_be_between_1_and_31(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate() + timedelta(days=30)
        self.user.save(update_fields=["plan", "premium_until"])

        for value in (0, 32):
            with self.subTest(value=value):
                serializer = UserSerializer(
                    self.user,
                    data={"completed_items_retention_days": value},
                    partial=True,
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn("completed_items_retention_days", serializer.errors)

    def test_premium_expiring_today_can_still_change_retention_days(self):
        self.user.plan = "PR"
        self.user.premium_until = timezone.localdate()
        self.user.save(update_fields=["plan", "premium_until"])
        serializer = UserSerializer(
            self.user,
            data={"completed_items_retention_days": 30},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
