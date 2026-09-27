import uuid
from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.saved_items.extraction.parser import ParsedContent
from apps.saved_items.extraction.pipeline import run_extraction
from apps.saved_items.models import SavedItem
from apps.users.models import CustomUser


def create_user(email="user1@example.com"):
    return CustomUser.objects.create_user(
        email=email, password="strong-pass-123", first_name="Test",
    )


class ExtractionRaceConditionIntegrationTests(APITestCase):
    """
    شبیه‌سازی خودکار همون چیزی که امروز دستی با broker واقعی دیدیم:
    چند بار پشت‌سرهم url از طریق API واقعی عوض می‌شه (هر بار یه task
    جدید با یه نسخه‌ی جدید صف می‌شه)، ولی worker به‌ترتیب اجرا نمی‌کنه.
    فقط لایه‌ی شبکه/broker mock می‌شه؛ مسیر واقعی API → services →
    versioning → pipeline کاملاً واقعیه.
    """

    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def _patch_url_via_api(self, item_id, new_url):
        """
        url رو از طریق API واقعی عوض می‌کنه و نسخه‌ی extraction تازه‌ی
        بعد از این تغییر رو برمی‌گردونه — بدون اجرای واقعی task (callback
        رو capture می‌کنیم ولی صداش نمی‌زنیم، دقیقاً شبیه یه task که
        هنوز توی صف منتظر مونده و اجرا نشده).
        """
        with self.captureOnCommitCallbacks(execute=False):
            response = self.client.patch(
                reverse('saved-item-detail', args=[item_id]),
                {"url": new_url},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = SavedItem.objects.get(pk=item_id)
        return str(item.extraction_version)

    def _fake_extraction_result(self, title):
        return ParsedContent(metadata={"title": title}, body_text=None)

    @patch("apps.saved_items.extraction.pipeline.parse_fetch_result")
    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_out_of_order_execution_final_state_matches_latest_url(
        self, mock_fetch, mock_parse,
    ):
        """
        سناریوی دقیق خودمون: POST با url=A (نسخه‌ی v_a صف می‌شه)، بلافاصله
        PATCH با url=B (نسخه‌ی v_b صف می‌شه). ولی worker برعکس اجرا می‌کنه:
        اول task مال B، بعد (دیرتر) task مال A. نتیجه‌ی نهایی باید مال B
        باشه، نه اینکه A آخرین بار بنویسه و برنده بشه.
        """
        mock_fetch.return_value = MagicMock()

        # ۱. POST با url=A
        with self.captureOnCommitCallbacks(execute=False):
            create_response = self.client.post(
                reverse('saved-item-list'),
                {"name": "Race test", "url": "https://example.com/a"},
                format="json",
            )
        item_id = create_response.data["id"]
        version_a = str(SavedItem.objects.get(pk=item_id).extraction_version)

        # ۲. بلافاصله PATCH با url=B — نسخه‌ی جدید
        version_b = self._patch_url_via_api(item_id, "https://example.com/b")
        self.assertNotEqual(version_a, version_b)

        # ۳. worker برعکس ترتیب صف اجرا می‌کنه: اول B (جدیدتر) موفق می‌شه...
        mock_parse.return_value = self._fake_extraction_result("Content of B")
        run_extraction(item_id, version_b)

        item = SavedItem.objects.get(pk=item_id)
        self.assertEqual(item.metadata["title"], "Content of B")
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)

        # ۴. ...و بعد، دیرتر، task قدیمی مال A بالاخره اجرا می‌شه
        mock_parse.return_value = self._fake_extraction_result("Stale content of A")
        run_extraction(item_id, version_a)

        # نتیجه‌ی B باید دست‌نخورده بمونه — A نباید overwrite کنه
        item.refresh_from_db()
        self.assertEqual(item.metadata["title"], "Content of B")
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)

    @patch("apps.saved_items.extraction.pipeline.parse_fetch_result")
    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_three_rapid_url_changes_only_last_version_can_write(
        self, mock_fetch, mock_parse,
    ):
        """
        نسخه‌ی سخت‌گیرانه‌تر: سه بار پشت‌سرهم url عوض می‌شه (سه تا نسخه‌ی
        متفاوت صف می‌شن)، و همه‌ی سه تا task به هر ترتیبی که فکرش رو بکنی
        اجرا می‌شن (حتی معکوس کامل). فقط آخرین نسخه باید موفق به نوشتن بشه.
        """
        mock_fetch.return_value = MagicMock()

        with self.captureOnCommitCallbacks(execute=False):
            create_response = self.client.post(
                reverse('saved-item-list'),
                {"name": "Triple race", "url": "https://example.com/v1"},
                format="json",
            )
        item_id = create_response.data["id"]
        version_1 = str(SavedItem.objects.get(pk=item_id).extraction_version)
        version_2 = self._patch_url_via_api(item_id, "https://example.com/v2")
        version_3 = self._patch_url_via_api(item_id, "https://example.com/v3")

        self.assertEqual(len({version_1, version_2, version_3}), 3)  # هر سه متفاوتن

        # اجرا به ترتیب کاملاً معکوس: ۳ (جدیدترین) اول، بعد ۲، بعد ۱ (قدیمی‌ترین)
        for version, title in [
            (version_3, "Content v3"),
            (version_2, "Content v2 (should be rejected)"),
            (version_1, "Content v1 (should be rejected)"),
        ]:
            mock_parse.return_value = self._fake_extraction_result(title)
            run_extraction(item_id, version)

        item = SavedItem.objects.get(pk=item_id)
        self.assertEqual(item.metadata["title"], "Content v3")
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)

    def test_task_for_deleted_item_does_not_raise(self):
        """
        سناریوی مرتبط: کاربر آیتم رو کامل حذف می‌کنه در حالی که یه task
        قدیمی هنوز توی صفه. task باید بی‌سروصدا skip بشه، نه اینکه بترکه.
        """
        with self.captureOnCommitCallbacks(execute=False):
            create_response = self.client.post(
                reverse('saved-item-list'),
                {"name": "Will be deleted", "url": "https://example.com/gone"},
                format="json",
            )
        item_id = create_response.data["id"]
        version = str(SavedItem.objects.get(pk=item_id).extraction_version)

        delete_response = self.client.delete(reverse('saved-item-detail', args=[item_id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        run_extraction(item_id, version)  # نباید exception بده
