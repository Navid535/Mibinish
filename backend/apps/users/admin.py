from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import render

from unfold.admin import ModelAdmin
from unfold.forms import (
    UserChangeForm,
    UserCreationForm,
    AdminPasswordChangeForm,
)

from apps.users.forms import ActivatePremiumForm
from apps.users.models import CustomUser
from apps.users.services import activate_premium, PremiumServiceError


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ('first_name', 'last_name', 'email')

    list_display = (
        'email',
        'first_name',
        'last_name',
        'plan',
        'premium_until',
        'is_staff',
        'is_active',
    )

    list_filter = (
        'plan',
        'is_staff',
        'is_superuser',
        'is_active',
    )

    search_fields = (
        'email',
        'first_name',
        'last_name',
    )

    readonly_fields = (
        'last_login',
        'date_joined',
    )

    fieldsets = (
        (None, {
            'fields': (
                'email',
                'password',
            )
        }),
        ('Personal info', {
            'fields': (
                'first_name',
                'last_name',
            )
        }),
        ('Plan', {
            'fields': (
                'plan',
                'premium_until',
                'completed_items_retention_days',
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        ('Important dates', {
            'fields': (
                'last_login',
                'date_joined',
            ),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'password1',
                'password2',
            ),
        }),
    )

    actions = [
        'activate_premium_action',
    ]

    @admin.action(description="Activate/renew premium for selected users")
    def activate_premium_action(self, request, queryset):
        if 'apply' in request.POST:
            form = ActivatePremiumForm(request.POST)

            if form.is_valid():
                days = form.cleaned_data['days']
                succeeded = 0
                errors = []

                for user in queryset:
                    try:
                        activate_premium(user, days=days)
                        succeeded += 1
                    except PremiumServiceError as exc:
                        errors.append(f"{user.email}: {exc}")

                if succeeded:
                    self.message_user(
                        request,
                        f"Activated/renewed premium for {succeeded} user(s).",
                        level=messages.SUCCESS,
                    )

                for error in errors:
                    self.message_user(
                        request,
                        error,
                        level=messages.ERROR,
                    )

                return None

        form = ActivatePremiumForm(
            initial={
                '_selected_action': queryset.values_list('pk', flat=True)
            }
        )

        return render(
            request,
            'admin/users/activate_premium.html',
            {
                'users': queryset,
                'form': form,
                'opts': self.model._meta,
            },
        )