import uuid
import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError


from apps.saved_items.extraction.parser import derive_source
from apps.saved_items.models import SavedItem, SavedItemCategory

logger = logging.getLogger(__name__)


FREE_ITEM_LIMIT = 100
PREMIUM_ITEM_LIMIT = 500


def _get_item_limit(user):
    if user.plan == "PR":
        return PREMIUM_ITEM_LIMIT

    return FREE_ITEM_LIMIT


def _check_item_limit(user):
    item_limit = _get_item_limit(user)
    item_count = user.saved_items.count()

    if item_count >= item_limit:
        raise ValidationError(
            f"You have reached your limit of {item_limit} saved items."
        )

@transaction.atomic
def create_saved_item(*, user, category_links=None, **fields):
    _check_item_limit(user)

    if not fields.get('url'):
        fields['extraction_status'] = SavedItem.ExtractionStatus.NO_URL
    else:
        fields['source'] = derive_source(fields['url'])

    status = fields.get('status', SavedItem.Status.TO_DO)
    fields['completed_at'] = timezone.now() if status == SavedItem.Status.COMPLETED else None

    saved_item = SavedItem.objects.create(user=user, **fields)
    _sync_categories(saved_item, category_links or [])

    if saved_item.url:
        _queue_extraction(saved_item)

    return saved_item


@transaction.atomic
def update_saved_item(*, saved_item, category_links=None, **fields):
    if 'status' in fields and fields['status'] != saved_item.status:
        fields['completed_at'] = (
            timezone.now() if fields['status'] == SavedItem.Status.COMPLETED else None
        )

    url_changed = 'url' in fields and fields['url'] != saved_item.url
    if url_changed:
        fields['extraction_version'] = uuid.uuid4()
        if fields['url']:
            fields['source'] = derive_source(fields['url'])
            fields['extraction_status'] = SavedItem.ExtractionStatus.PENDING
        else:
            fields['source'] = ''
            fields['extraction_status'] = SavedItem.ExtractionStatus.NO_URL
        fields['extracted_content'] = None
        fields['metadata'] = None
        fields['extraction_error'] = None

    for field, value in fields.items():
        setattr(saved_item, field, value)
    saved_item.save()

    if category_links is not None:
        _sync_categories(saved_item, category_links)

    if url_changed and saved_item.url:
        _queue_extraction(saved_item)

    return saved_item


def _queue_extraction(saved_item):
    from apps.saved_items.tasks import extract_content_task

    version = str(saved_item.extraction_version)

    def _delay():
        try:
            extract_content_task.delay(saved_item.id, version)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to queue extraction task for SavedItem %s", saved_item.id
            )
            SavedItem.objects.filter(
                pk=saved_item.id, extraction_version=version,
            ).update(
                extraction_status=SavedItem.ExtractionStatus.FAILED,
                extraction_error="Could not queue extraction task (broker unavailable)",
            )

    transaction.on_commit(_delay)

def _sync_categories(saved_item, category_links):
    saved_item.category_links.all().delete()
    SavedItemCategory.objects.bulk_create([
        SavedItemCategory(
            saved_item=saved_item,
            category=link['category'],
            priority=link.get('priority', 1),
        )
        for link in category_links
    ])