from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.users.models import CustomUser

class PremiumServiceError(Exception):
    """Raised when a premium activation request is invalid."""

def activate_premium(user: CustomUser, days: int) -> CustomUser:
    if days <= 0:
        raise PremiumServiceError("days must be a positive integer")

    today = timezone.localdate()

    with transaction.atomic():
        user = CustomUser.objects.select_for_update().get(pk=user.pk)

        has_active_premium = (
            user.plan == "PR"
            and user.premium_until is not None
            and user.premium_until >= today
        )

        base_date = user.premium_until if has_active_premium else today

        user.plan = "PR"
        user.premium_until = base_date + timedelta(days=days)

        user.save(
            update_fields=[
                "plan",
                "premium_until",
            ]
        )

    return user
