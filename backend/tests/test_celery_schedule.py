from celery.schedules import crontab
from django.conf import settings
from django.test import TestCase


class CeleryBeatScheduleTests(TestCase):
    def test_schedule_contains_expected_entries(self):
        self.assertIn("expire-premium-users-daily", settings.CELERY_BEAT_SCHEDULE)
        self.assertIn(
            "purge-expired-completed-items-daily", settings.CELERY_BEAT_SCHEDULE
        )

    def test_expire_premium_users_entry(self):
        entry = settings.CELERY_BEAT_SCHEDULE["expire-premium-users-daily"]
        self.assertEqual(entry["task"], "apps.users.tasks.expire_premium_users")
        self.assertEqual(entry["schedule"], crontab(hour=0, minute=0))

    def test_purge_expired_completed_items_entry(self):
        entry = settings.CELERY_BEAT_SCHEDULE["purge-expired-completed-items-daily"]
        self.assertEqual(
            entry["task"], "apps.saved_items.tasks.purge_expired_completed_items"
        )
        self.assertEqual(entry["schedule"], crontab(hour=0, minute=30))

    def test_the_two_tasks_do_not_run_at_the_same_time(self):
        expire_schedule = settings.CELERY_BEAT_SCHEDULE["expire-premium-users-daily"][
            "schedule"
        ]
        purge_schedule = settings.CELERY_BEAT_SCHEDULE[
            "purge-expired-completed-items-daily"
        ]["schedule"]
        self.assertNotEqual(expire_schedule, purge_schedule)
