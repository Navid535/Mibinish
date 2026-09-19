from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.users.models import CustomUser
from apps.users.tasks import expire_premium_users

class ExpirePremiumUsersTests(TestCase):
    def test_expires_users_whose_premium_ended(self):
        today = timezone.localdate()


        expired_user = CustomUser.objects.create_user(
            email="expired@example.com",
            first_name="Expired",
            password="secret123",
        )
        expired_user.plan = "PR"
        expired_user.premium_until = today - timedelta(days=1)
        expired_user.save()

        updated_count = expire_premium_users()

        expired_user.refresh_from_db()

        self.assertEqual(updated_count, 1)
        self.assertEqual(expired_user.plan, "FR")
        self.assertIsNone(expired_user.premium_until)

    def test_keeps_active_premium_users(self):
        today = timezone.localdate()

        user = CustomUser.objects.create_user(
            email="active@example.com",
            first_name="Active",
            password="secret123",
        )
        user.plan = "PR"
        user.premium_until = today + timedelta(days=1)
        user.save()

        updated_count = expire_premium_users()

        user.refresh_from_db()

        self.assertEqual(updated_count, 0)
        self.assertEqual(user.plan, "PR")
        self.assertEqual(
            user.premium_until,
            today + timedelta(days=1),
        )

    def test_keeps_premium_expiring_today(self):
        today = timezone.localdate()

        user = CustomUser.objects.create_user(
            email="today@example.com",
            first_name="Today",
            password="secret123",
        )
        user.plan = "PR"
        user.premium_until = today
        user.save()

        updated_count = expire_premium_users()

        user.refresh_from_db()

        self.assertEqual(updated_count, 0)
        self.assertEqual(user.plan, "PR")
        self.assertEqual(user.premium_until, today)

    def test_expires_multiple_users(self):
        today = timezone.localdate()

        for email, first_name in (
            ("one@example.com", "One"),
            ("two@example.com", "Two"),
            ("three@example.com", "Three"),
        ):
            user = CustomUser.objects.create_user(
                email=email,
                first_name=first_name,
                password="secret123",
            )
            user.plan = "PR"
            user.premium_until = today - timedelta(days=1)
            user.save()

        updated_count = expire_premium_users()

        self.assertEqual(updated_count, 3)

        self.assertEqual(
            CustomUser.objects.filter(plan="PR").count(),
            0,
        )

