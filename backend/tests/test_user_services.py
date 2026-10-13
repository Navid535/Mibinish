from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.users.models import CustomUser
from apps.users.services import PremiumServiceError, activate_premium


class ActivatePremiumTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="[john@example.com](mailto:john@example.com)",
            first_name="John",
            password="secret123",
        )

    def test_activates_premium_for_free_user(self):
        today = timezone.localdate()

        user = activate_premium(self.user, 30)

        self.assertEqual(user.plan, "PR")
        self.assertEqual(user.premium_until, today + timedelta(days=30))

    def test_extends_active_premium(self):
        today = timezone.localdate()
        self.user.plan = "PR"
        self.user.premium_until = today + timedelta(days=10)
        self.user.save()

        user = activate_premium(self.user, 30)

        self.assertEqual(user.plan, "PR")
        self.assertEqual(
            user.premium_until,
            today + timedelta(days=40),
        )

    def test_reactivates_expired_premium_from_today(self):
        today = timezone.localdate()
        self.user.plan = "PR"
        self.user.premium_until = today - timedelta(days=5)
        self.user.save()

        user = activate_premium(self.user, 30)

        self.assertEqual(user.plan, "PR")
        self.assertEqual(
            user.premium_until,
            today + timedelta(days=30),
        )

    def test_rejects_zero_days(self):
        with self.assertRaises(PremiumServiceError):
            activate_premium(self.user, 0)

    def test_rejects_negative_days(self):
        with self.assertRaises(PremiumServiceError):
            activate_premium(self.user, -1)
