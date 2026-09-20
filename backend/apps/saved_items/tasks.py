from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.saved_items.models import SavedItem
from apps.users.models import CustomUser


@shared_task
def purge_expired_completed_items() -> int:
    now = timezone.now()
    total_deleted = 0

    retention_days_values = (
        CustomUser.objects
        .filter(saved_items__status=SavedItem.Status.COMPLETED)
        .values_list('completed_items_retention_days', flat=True)
        .distinct()
    )

    for days in retention_days_values:
        cutoff = now - timedelta(days=days)
        queryset = SavedItem.objects.filter(
            status=SavedItem.Status.COMPLETED,
            completed_at__lte=cutoff,
            user__completed_items_retention_days=days,
        )
        deleted_count = queryset.count()
        queryset.delete()
        total_deleted += deleted_count

    return total_deleted