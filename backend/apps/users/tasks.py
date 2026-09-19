from celery import shared_task
from django.utils import timezone

from apps.users.models import CustomUser


@shared_task
def expire_premium_users() -> int:
    today = timezone.localdate()

    updated_count = CustomUser.objects.filter(
        plan="PR",
        premium_until__lt=today,
    ).update(plan="FR", premium_until=None)

    # TODO: change this to send email to user

    return updated_count