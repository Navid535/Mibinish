import logging

from apps.saved_items.extraction.fetcher import FetchError, fetch_url
from apps.saved_items.extraction.parser import ParsedContent, parse_fetch_result
from apps.saved_items.models import SavedItem

logger = logging.getLogger(__name__)


def run_extraction(saved_item_id: int, expected_version: str) -> None:
    """
    Fetch + parse content for a SavedItem and persist the outcome.

    Never raises for ordinary failures (network issues, non-HTML content,
    parsing edge cases) — those are recorded as a FAILED status with a
    short error message. A SavedItem's retention, and the rest of the
    app, never depends on this succeeding.
    """
    try:
        saved_item = SavedItem.objects.get(pk=saved_item_id)
    except SavedItem.DoesNotExist:
        logger.warning("SavedItem %s no longer exists; skipping extraction", saved_item_id)
        return

    if str(saved_item.extraction_version) != expected_version:
        logger.info("Stale extraction task for SavedItem %s; skipping", saved_item_id)
        return

    if not saved_item.url:
        _mark_no_url(saved_item_id, expected_version)
        return

    _mark_processing(saved_item_id, expected_version)

    try:
        fetch_result = fetch_url(saved_item.url)
        parsed = parse_fetch_result(fetch_result)
    except FetchError as exc:
        _mark_failed(saved_item_id, str(exc), expected_version)
        return
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected extraction error for SavedItem %s", saved_item_id)
        _mark_failed(saved_item_id, "Unexpected error during extraction", expected_version)
        return

    _mark_done(saved_item_id, parsed, expected_version)



def _mark_processing(saved_item_id: int, expected_version: str) -> None:
    SavedItem.objects.filter(
        pk=saved_item_id, extraction_version=expected_version,
    ).update(
        extraction_status=SavedItem.ExtractionStatus.PROCESSING,
        extraction_error=None,
    )


def _mark_no_url(saved_item_id: int, expected_version: str) -> None:
    SavedItem.objects.filter(
        pk=saved_item_id, extraction_version=expected_version,
    ).update(
        extraction_status=SavedItem.ExtractionStatus.NO_URL,
        extraction_error=None,
    )


def _mark_failed(saved_item_id: int, error_message: str, expected_version: str) -> None:
    SavedItem.objects.filter(
        pk=saved_item_id, extraction_version=expected_version,
    ).update(
        extraction_status=SavedItem.ExtractionStatus.FAILED,
        extraction_error=error_message[:1000],
    )


def _mark_done(saved_item_id: int, parsed: ParsedContent, expected_version: str) -> None:
    SavedItem.objects.filter(
        pk=saved_item_id, extraction_version=expected_version,
    ).update(
        extraction_status=SavedItem.ExtractionStatus.DONE,
        extraction_error=None,
        metadata=parsed.metadata,
        extracted_content={"body_text": parsed.body_text} if parsed.body_text else None,
    )