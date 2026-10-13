from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    def _create_user(self, email, password, first_name, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        extra_fields.pop("email", None)
        extra_fields.pop("first_name", None)

        user = self.model(email=email, first_name=first_name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        first_name = extra_fields.pop("first_name", None)
        if not first_name:
            raise ValueError("Users must have a first name")
        return self._create_user(email, password, first_name, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        first_name = extra_fields.pop("first_name", None)
        if not first_name:
            raise ValueError("Users must have a first name")
        return self._create_user(email, password, first_name, **extra_fields)


class CustomUser(AbstractUser):
    PLAN_CHOICES = (
        ("PR", "Premium"),
        ("FR", "Free"),
    )

    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=21)
    last_name = models.CharField(max_length=21, null=True, blank=True)

    plan = models.CharField(max_length=2, choices=PLAN_CHOICES, default="FR")
    premium_until = models.DateField(null=True, blank=True)
    completed_items_retention_days = models.PositiveIntegerField(default=7)

    class Meta:
        ordering = ["first_name", "last_name", "email"]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]

    objects = UserManager()

    @property
    def full_name(self):
        if self.last_name:
            return f"{self.first_name.strip()} {self.last_name.strip()}"
        else:
            return self.first_name.strip()

    def __str__(self):
        return self.full_name
