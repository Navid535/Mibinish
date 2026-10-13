import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class CategoryQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        return self.filter(user=user).distinct()


class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="categories", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=9, default="#3299a8")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "name"),
                name="unique_category_name_per_user",
            )
        ]

    objects = CategoryQuerySet.as_manager()

    def __str__(self):
        return self.name


class SavedItemQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        return self.filter(user=user).distinct()


class SavedItem(models.Model):
    class Status(models.TextChoices):
        TO_DO = "to_do", "To Do"
        COMPLETED = "completed", "Completed"

    class ExtractionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        NO_URL = "no_url", "No URL"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="saved_items", on_delete=models.CASCADE
    )
    categories = models.ManyToManyField(
        Category,
        through="SavedItemCategory",
        related_name="saved_items",
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    url = models.URLField(max_length=500, null=True, blank=True)
    source = models.CharField(max_length=50, blank=True)

    extracted_content = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    extraction_status = models.CharField(
        max_length=20,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.PENDING,
    )
    extraction_error = models.TextField(null=True, blank=True)
    extraction_version = models.UUIDField(default=uuid.uuid4, editable=False)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TO_DO
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SavedItemQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at", "-completed_at", "name")
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(name__isnull=False) | models.Q(url__isnull=False)),
                name="saved_item_name_or_url_required",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="to_do", completed_at__isnull=True)
                    | models.Q(status="completed", completed_at__isnull=False)
                ),
                name="saved_item_status_completed_at_consistent",
            ),
        ]

    def __str__(self):
        return self.name or self.url


class SavedItemCategory(models.Model):
    saved_item = models.ForeignKey(
        SavedItem, related_name="category_links", on_delete=models.CASCADE
    )
    category = models.ForeignKey(
        Category, related_name="item_links", on_delete=models.CASCADE
    )
    priority = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("saved_item", "category"),
                name="unique_saved_item_category",
            )
        ]

    def __str__(self):
        return f"{self.saved_item} → {self.category}"
