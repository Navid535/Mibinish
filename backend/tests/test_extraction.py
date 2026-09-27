import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.saved_items import services
from apps.saved_items.extraction.fetcher import FetchError, FetchResult, fetch_url
from apps.saved_items.extraction.parser import derive_source, parse_fetch_result
from apps.saved_items.extraction.pipeline import run_extraction
from apps.saved_items.extraction.security import UnsafeURLError, assert_url_is_safe
from apps.saved_items.models import SavedItem
from apps.users.models import CustomUser


def create_user(email="user1@example.com"):
    return CustomUser.objects.create_user(
        email=email, password="strong-pass-123", first_name="Test",
    )


# ---------------------------------------------------------------------
# security.py
# ---------------------------------------------------------------------

class SecurityTests(TestCase):
    @patch("apps.saved_items.extraction.security.socket.getaddrinfo")
    def test_public_ip_is_allowed(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
        assert_url_is_safe("https://example.com")

    @patch("apps.saved_items.extraction.security.socket.getaddrinfo")
    def test_loopback_ip_is_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        with self.assertRaises(UnsafeURLError):
            assert_url_is_safe("http://localhost")

    @patch("apps.saved_items.extraction.security.socket.getaddrinfo")
    def test_private_ip_is_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("10.0.0.5", 0))]
        with self.assertRaises(UnsafeURLError):
            assert_url_is_safe("http://internal.example.com")

    @patch("apps.saved_items.extraction.security.socket.getaddrinfo")
    def test_link_local_ip_is_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("169.254.169.254", 0))]
        with self.assertRaises(UnsafeURLError):
            assert_url_is_safe("http://169.254.169.254/latest/meta-data/")

    def test_disallowed_scheme_is_rejected(self):
        with self.assertRaises(UnsafeURLError):
            assert_url_is_safe("file:///etc/passwd")

    @patch("apps.saved_items.extraction.security.socket.getaddrinfo")
    def test_dns_failure_is_rejected(self, mock_getaddrinfo):
        import socket
        mock_getaddrinfo.side_effect = socket.gaierror("name resolution failed")
        with self.assertRaises(UnsafeURLError):
            assert_url_is_safe("https://this-does-not-resolve.invalid")


# ---------------------------------------------------------------------
# fetcher.py
# ---------------------------------------------------------------------

def _mock_response(status_code=200, content_type="text/html; charset=utf-8",
                    body=b"<html></html>", location=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = {"Content-Type": content_type}
    if location:
        response.headers["Location"] = location
    response.is_redirect = location is not None
    response.iter_content.return_value = [body]
    return response


class FetcherTests(TestCase):
    @patch("apps.saved_items.extraction.fetcher.assert_url_is_safe")
    @patch("requests.Session.get")
    def test_successful_fetch_returns_content(self, mock_get, mock_safe):
        mock_get.return_value = _mock_response(body=b"<html><body>hi</body></html>")
        result = fetch_url("https://example.com")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content_type, "text/html")
        self.assertEqual(result.charset, "utf-8")
        self.assertIn(b"hi", result.content)

    @patch("apps.saved_items.extraction.fetcher.assert_url_is_safe")
    @patch("requests.Session.get")
    def test_redirect_is_followed_and_rechecked(self, mock_get, mock_safe):
        mock_get.side_effect = [
            _mock_response(status_code=302, location="https://example.com/final"),
            _mock_response(body=b"<html>final</html>"),
        ]
        result = fetch_url("https://example.com/start")
        self.assertEqual(result.final_url, "https://example.com/final")
        self.assertEqual(mock_safe.call_count, 2)

    @patch("apps.saved_items.extraction.fetcher.assert_url_is_safe")
    @patch("requests.Session.get")
    def test_too_many_redirects_raises_fetch_error(self, mock_get, mock_safe):
        mock_get.return_value = _mock_response(status_code=302, location="https://example.com/loop")
        with self.assertRaises(FetchError):
            fetch_url("https://example.com/loop")

    @patch("apps.saved_items.extraction.fetcher.assert_url_is_safe")
    def test_unsafe_url_raises_fetch_error(self, mock_safe):
        mock_safe.side_effect = UnsafeURLError("blocked")
        with self.assertRaises(FetchError):
            fetch_url("http://169.254.169.254/")

    @patch("apps.saved_items.extraction.fetcher.assert_url_is_safe")
    @patch("requests.Session.get")
    def test_non_2xx_status_raises_fetch_error(self, mock_get, mock_safe):
        mock_get.return_value = _mock_response(status_code=404)
        with self.assertRaises(FetchError):
            fetch_url("https://example.com/missing")

    @patch("apps.saved_items.extraction.fetcher.assert_url_is_safe")
    @patch("requests.Session.get")
    def test_oversized_body_raises_fetch_error(self, mock_get, mock_safe):
        from apps.saved_items.extraction import fetcher as fetcher_module
        response = _mock_response()
        response.iter_content.return_value = [b"x" * (fetcher_module.MAX_CONTENT_BYTES + 1)]
        mock_get.return_value = response
        with self.assertRaises(FetchError):
            fetch_url("https://example.com/huge")

    @patch("apps.saved_items.extraction.fetcher.assert_url_is_safe")
    @patch("requests.Session.get")
    def test_connection_error_raises_fetch_error(self, mock_get, mock_safe):
        import requests
        mock_get.side_effect = requests.ConnectionError("boom")
        with self.assertRaises(FetchError):
            fetch_url("https://example.com/down")


# ---------------------------------------------------------------------
# parser.py
# ---------------------------------------------------------------------

class DeriveSourceTests(TestCase):
    def test_known_domain_maps_to_label(self):
        self.assertEqual(derive_source("https://www.instagram.com/p/xyz/"), "Instagram")
        self.assertEqual(derive_source("https://t.me/somechannel"), "Telegram")

    def test_subdomain_of_known_domain_maps_to_label(self):
        self.assertEqual(derive_source("https://old.reddit.com/r/django"), "Reddit")

    def test_unknown_domain_returns_hostname(self):
        self.assertEqual(derive_source("https://my-personal-blog.example"), "my-personal-blog.example")

    def test_www_prefix_is_stripped(self):
        self.assertEqual(derive_source("https://www.example.com/page"), "example.com")


class ParseFetchResultTests(TestCase):
    def test_html_extracts_og_metadata(self):
        html = b"""
        <html><head>
            <meta property="og:title" content="Cool Article">
            <meta property="og:description" content="A description">
            <meta property="og:image" content="https://example.com/img.png">
        </head><body><article><p>Some body text here.</p></article></body></html>
        """
        result = FetchResult(
            final_url="https://example.com/a", status_code=200,
            content_type="text/html", charset="utf-8", content=html,
        )
        parsed = parse_fetch_result(result)
        self.assertEqual(parsed.metadata["title"], "Cool Article")
        self.assertIn("Some body text here.", parsed.body_text)

    def test_non_html_content_returns_metadata_only(self):
        result = FetchResult(
            final_url="https://example.com/file.pdf", status_code=200,
            content_type="application/pdf", charset=None, content=b"%PDF-1.4...",
        )
        parsed = parse_fetch_result(result)
        self.assertEqual(parsed.metadata["content_type"], "application/pdf")
        self.assertIsNone(parsed.body_text)

    def test_malformed_html_does_not_crash(self):
        html = b"<html><body><p>unclosed tag <div>whatever"
        result = FetchResult(
            final_url="https://example.com/broken", status_code=200,
            content_type="text/html", charset="utf-8", content=html,
        )
        parsed = parse_fetch_result(result)
        self.assertIsInstance(parsed.metadata, dict)


# ---------------------------------------------------------------------
# pipeline.py — شامل چک نسخه
# ---------------------------------------------------------------------

class RunExtractionTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_missing_saved_item_does_not_raise(self):
        run_extraction(saved_item_id=999999, expected_version=str(uuid.uuid4()))

    def test_item_without_url_marks_no_url(self):
        item = SavedItem.objects.create(user=self.user, name="No URL item")
        run_extraction(item.id, str(item.extraction_version))
        item.refresh_from_db()
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.NO_URL)

    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_fetch_error_marks_failed_with_message(self, mock_fetch):
        mock_fetch.side_effect = FetchError("host unreachable")
        item = SavedItem.objects.create(user=self.user, url="https://example.com")

        run_extraction(item.id, str(item.extraction_version))

        item.refresh_from_db()
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.FAILED)
        self.assertIn("host unreachable", item.extraction_error)

    @patch("apps.saved_items.extraction.pipeline.parse_fetch_result")
    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_successful_extraction_marks_done_and_saves_data(self, mock_fetch, mock_parse):
        from apps.saved_items.extraction.parser import ParsedContent
        mock_fetch.return_value = MagicMock()
        mock_parse.return_value = ParsedContent(metadata={"title": "Hello"}, body_text="Full body text")
        item = SavedItem.objects.create(user=self.user, url="https://example.com")

        run_extraction(item.id, str(item.extraction_version))

        item.refresh_from_db()
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)
        self.assertEqual(item.metadata["title"], "Hello")
        self.assertEqual(item.extracted_content["body_text"], "Full body text")

    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_unexpected_exception_marks_failed_without_crashing(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("totally unexpected bug")
        item = SavedItem.objects.create(user=self.user, url="https://example.com")

        run_extraction(item.id, str(item.extraction_version))  # نباید exception بیرون بده

        item.refresh_from_db()
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.FAILED)

    @patch("apps.saved_items.extraction.pipeline.parse_fetch_result")
    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_concurrent_field_change_is_not_overwritten(self, mock_fetch, mock_parse):
        from apps.saved_items.extraction.parser import ParsedContent
        mock_fetch.return_value = MagicMock()
        mock_parse.return_value = ParsedContent(metadata={"title": "X"}, body_text=None)
        item = SavedItem.objects.create(user=self.user, url="https://example.com", name="Original")

        SavedItem.objects.filter(pk=item.pk).update(name="Changed by user")

        run_extraction(item.id, str(item.extraction_version))

        item.refresh_from_db()
        self.assertEqual(item.name, "Changed by user")
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)

    def test_stale_version_at_start_is_skipped_entirely(self):
        """
        شبیه‌سازی: task قدیمی، بعد از این‌که نسخه‌ی آیتم عوض شده، اجرا می‌شه.
        باید بلافاصله (قبل از هر fetch) skip بشه.
        """
        item = SavedItem.objects.create(user=self.user, url="https://example.com")
        stale_version = str(item.extraction_version)

        SavedItem.objects.filter(pk=item.pk).update(extraction_version=uuid.uuid4())

        with patch("apps.saved_items.extraction.pipeline.fetch_url") as mock_fetch:
            run_extraction(item.id, stale_version)
            mock_fetch.assert_not_called()  # اصلاً نباید تلاش کنه fetch کنه

    @patch("apps.saved_items.extraction.pipeline.parse_fetch_result")
    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_version_change_mid_execution_prevents_final_write(self, mock_fetch, mock_parse):
        """
        دقیقاً همون TOCTOU که بحثش کردیم: نسخه در لحظه‌ی شروع درست بود
        (_mark_processing موفق می‌شه)، ولی *وسط* fetch_url، یه task
        دیگه (شبیه‌سازی‌شده) نسخه رو عوض می‌کنه. نتیجه‌ی این task باید
        دور ریخته بشه، نه این‌که رکورد رو overwrite کنه.
        """
        from apps.saved_items.extraction.parser import ParsedContent

        item = SavedItem.objects.create(user=self.user, url="https://example.com")
        original_version = str(item.extraction_version)

        def fetch_side_effect(url):
            # شبیه‌سازی این‌که وسط fetch، یه update_saved_item دیگه اجرا شده
            SavedItem.objects.filter(pk=item.pk).update(extraction_version=uuid.uuid4())
            return MagicMock()

        mock_fetch.side_effect = fetch_side_effect
        mock_parse.return_value = ParsedContent(metadata={"title": "Should not be saved"}, body_text=None)

        run_extraction(item.id, original_version)

        item.refresh_from_db()
        # _mark_processing قبل از فچ موفق شده بود (نسخه هنوز match بود)،
        # ولی _mark_done نباید موفق بشه چون نسخه دیگه match نیست
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.PROCESSING)
        self.assertIsNone(item.metadata)


# ---------------------------------------------------------------------
# services.py — lifecycle کامل create/update + queue شدن task
# ---------------------------------------------------------------------

class CreateSavedItemExtractionLifecycleTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_create_with_url_queues_extraction_with_current_version(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            item = services.create_saved_item(user=self.user, url="https://example.com")

        self.assertEqual(len(callbacks), 1)

        with patch("apps.saved_items.tasks.extract_content_task.delay") as mock_delay:
            callbacks[0]()

        mock_delay.assert_called_once_with(item.id, str(item.extraction_version))

    def test_create_without_url_does_not_queue_extraction(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            services.create_saved_item(user=self.user, name="No URL")

        self.assertEqual(len(callbacks), 0)

    def test_create_with_url_sets_pending_status_and_source(self):
        item = services.create_saved_item(user=self.user, url="https://www.instagram.com/p/xyz/")
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.PENDING)
        self.assertEqual(item.source, "Instagram")


class UpdateSavedItemExtractionLifecycleTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_changing_url_bumps_version_and_queues_new_task(self):
        item = services.create_saved_item(user=self.user, url="https://example.com/a")
        original_version = item.extraction_version

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            updated = services.update_saved_item(saved_item=item, url="https://example.com/b")

        self.assertNotEqual(updated.extraction_version, original_version)
        self.assertEqual(updated.source, "example.com")
        self.assertEqual(updated.extraction_status, SavedItem.ExtractionStatus.PENDING)
        self.assertEqual(len(callbacks), 1)

        with patch("apps.saved_items.tasks.extract_content_task.delay") as mock_delay:
            callbacks[0]()
        mock_delay.assert_called_once_with(updated.id, str(updated.extraction_version))

    def test_changing_url_clears_previous_extracted_data(self):
        item = services.create_saved_item(user=self.user, url="https://example.com/a")
        SavedItem.objects.filter(pk=item.pk).update(
            extracted_content={"body_text": "old content"},
            metadata={"title": "old title"},
            extraction_status=SavedItem.ExtractionStatus.DONE,
        )

        updated = services.update_saved_item(saved_item=item, url="https://example.com/b")

        self.assertIsNone(updated.extracted_content)
        self.assertIsNone(updated.metadata)
        self.assertEqual(updated.extraction_status, SavedItem.ExtractionStatus.PENDING)

    def test_same_url_does_not_bump_version_or_queue(self):
        item = services.create_saved_item(user=self.user, url="https://example.com/a")
        original_version = item.extraction_version

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            updated = services.update_saved_item(saved_item=item, url="https://example.com/a", name="Renamed")

        self.assertEqual(updated.extraction_version, original_version)
        self.assertEqual(len(callbacks), 0)

    def test_removing_url_bumps_version_marks_no_url_and_does_not_queue(self):
        item = services.create_saved_item(user=self.user, url="https://example.com/a")
        original_version = item.extraction_version

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            updated = services.update_saved_item(saved_item=item, url=None, name="No URL now")

        self.assertNotEqual(updated.extraction_version, original_version)
        self.assertEqual(updated.extraction_status, SavedItem.ExtractionStatus.NO_URL)
        self.assertEqual(updated.source, "")
        self.assertEqual(len(callbacks), 0)  # چون url جدید خالیه، نباید queue بشه

    def test_update_without_url_field_does_not_touch_extraction_state(self):
        item = services.create_saved_item(user=self.user, url="https://example.com/a")
        original_version = item.extraction_version

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            updated = services.update_saved_item(saved_item=item, name="Just renaming")

        self.assertEqual(updated.extraction_version, original_version)
        self.assertEqual(len(callbacks), 0)


class FullExtractionRaceScenarioTests(TestCase):
    """
    سناریوی دقیق خودت: POST با url=A (task A صف می‌شه)، بلافاصله
    PATCH با url=B (task B صف می‌شه)، و task A دیرتر اجرا می‌شه.
    نتیجه‌ی A نباید نتیجه‌ی B رو overwrite کنه.
    """
    def setUp(self):
        self.user = create_user()

    @patch("apps.saved_items.extraction.pipeline.parse_fetch_result")
    @patch("apps.saved_items.extraction.pipeline.fetch_url")
    def test_late_stale_task_does_not_overwrite_newer_extraction(self, mock_fetch, mock_parse):
        from apps.saved_items.extraction.parser import ParsedContent

        # ۱. POST با url=A
        item = services.create_saved_item(user=self.user, url="https://example.com/a")
        version_a = str(item.extraction_version)

        # ۲. بلافاصله PATCH با url=B — نسخه عوض می‌شه
        item = services.update_saved_item(saved_item=item, url="https://example.com/b")
        version_b = str(item.extraction_version)
        self.assertNotEqual(version_a, version_b)

        # ۳. task B زودتر اجرا و موفق می‌شه
        mock_fetch.return_value = MagicMock()
        mock_parse.return_value = ParsedContent(metadata={"title": "B's content"}, body_text=None)
        run_extraction(item.id, version_b)

        item.refresh_from_db()
        self.assertEqual(item.metadata["title"], "B's content")
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)

        # ۴. task A (قدیمی، مال url=A) بالاخره دیر اجرا می‌شه
        mock_parse.return_value = ParsedContent(metadata={"title": "A's stale content"}, body_text=None)
        run_extraction(item.id, version_a)  # نسخه‌ی قدیمی

        # نتیجه‌ی B باید دست‌نخورده بمونه
        item.refresh_from_db()
        self.assertEqual(item.metadata["title"], "B's content")
        self.assertEqual(item.extraction_status, SavedItem.ExtractionStatus.DONE)