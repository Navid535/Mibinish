from django.db import transaction
from django.utils import timezone

from apps.saved_items.models import SavedItem, SavedItemCategory


@transaction.atomic
def create_saved_item(*, user, category_links=None, **fields):
    status = fields.get('status', SavedItem.Status.TO_DO)
    fields['completed_at'] = timezone.now() if status == SavedItem.Status.COMPLETED else None

    saved_item = SavedItem.objects.create(user=user, **fields)
    _sync_categories(saved_item, category_links or [])
    return saved_item


@transaction.atomic
def update_saved_item(*, saved_item, category_links=None, **fields):
    if 'status' in fields and fields['status'] != saved_item.status:
        fields['completed_at'] = (
            timezone.now() if fields['status'] == SavedItem.Status.COMPLETED else None
        )

    for field, value in fields.items():
        setattr(saved_item, field, value)
    saved_item.save()

    if category_links is not None:
        _sync_categories(saved_item, category_links)

    return saved_item


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