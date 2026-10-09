from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Tenant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        SUSPENDED = 'suspended', 'Suspended'

    name = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    trial_starts_at = models.DateTimeField(default=timezone.now)
    trial_ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                condition=Q(trial_ends_at__gt=models.F('trial_starts_at')),
                name='tenant_trial_ends_after_start',
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.trial_ends_at is None:
            self.trial_ends_at = self.trial_starts_at + timedelta(
                days=getattr(settings, 'DEFAULT_TRIAL_DAYS', 14)
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.trial_ends_at and self.trial_starts_at:
            if self.trial_ends_at <= self.trial_starts_at:
                raise ValidationError('Trial end must be after trial start.')


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        SUPER_VIEWER = 'super_viewer', 'Super Viewer'
        TENANT_ADMIN = 'tenant_admin', 'Tenant Admin'
        TENANT_USER = 'tenant_user', 'Tenant User'

    PLATFORM_ROLES = {
        Role.SUPER_ADMIN,
        Role.ADMIN,
        Role.SUPER_VIEWER,
    }
    TENANT_ROLES = {
        Role.TENANT_ADMIN,
        Role.TENANT_USER,
    }

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.TENANT_USER)
    tenant = models.ForeignKey(
        Tenant,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='users',
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        role__in=[
                            'super_admin',
                            'admin',
                            'super_viewer',
                        ],
                        tenant__isnull=True,
                    )
                    | Q(
                        role__in=[
                            'tenant_admin',
                            'tenant_user',
                        ],
                        tenant__isnull=False,
                    )
                ),
                name='user_role_tenant_membership_valid',
            ),
        ]

    def clean(self):
        super().clean()
        if self.role in self.PLATFORM_ROLES and self.tenant_id is not None:
            raise ValidationError('Platform users must not be assigned to a tenant.')
        if self.role in self.TENANT_ROLES and self.tenant_id is None:
            raise ValidationError('Tenant users must be assigned to a tenant.')

    def save(self, *args, **kwargs):
        if self.is_superuser and self.tenant_id is None and self.role == self.Role.TENANT_USER:
            self.role = self.Role.SUPER_ADMIN
        self.full_clean()
        super().save(*args, **kwargs)
