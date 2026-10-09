from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Tenant, User


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('health-check'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})


class TenantUserModelTests(TestCase):
    def test_new_tenant_gets_default_trial_end(self):
        starts_at = timezone.now()
        tenant = Tenant.objects.create(name='Example Institute', trial_starts_at=starts_at)

        self.assertEqual(tenant.status, Tenant.Status.ACTIVE)
        self.assertEqual(tenant.trial_ends_at, starts_at + timedelta(days=14))

    def test_database_rejects_invalid_trial_window(self):
        starts_at = timezone.now()

        with self.assertRaises(IntegrityError):
            Tenant.objects.bulk_create(
                [
                    Tenant(
                        name='Invalid Institute',
                        trial_starts_at=starts_at,
                        trial_ends_at=starts_at,
                    )
                ]
            )

    def test_platform_user_cannot_have_tenant(self):
        tenant = Tenant.objects.create(name='Example Institute')
        user = User(username='platform', role=User.Role.ADMIN, tenant=tenant, password='test')

        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_database_rejects_platform_user_with_tenant(self):
        tenant = Tenant.objects.create(name='Example Institute')

        with self.assertRaises(IntegrityError):
            User.objects.bulk_create(
                [
                    User(
                        username='platform-db',
                        role=User.Role.ADMIN,
                        tenant=tenant,
                        password='test',
                    )
                ]
            )

    def test_tenant_user_requires_tenant(self):
        user = User(username='learner', role=User.Role.TENANT_USER, password='test')

        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_database_rejects_tenant_user_without_tenant(self):
        with self.assertRaises(IntegrityError):
            User.objects.bulk_create(
                [User(username='learner-db', role=User.Role.TENANT_USER, password='test')]
            )

    def test_tenant_admin_with_tenant_is_valid(self):
        tenant = Tenant.objects.create(name='Example Institute')
        user = User(
            username='tenant-admin',
            role=User.Role.TENANT_ADMIN,
            tenant=tenant,
            password='test',
        )

        user.full_clean()

    def test_superuser_defaults_to_super_admin_role(self):
        user = User.objects.create_superuser(username='root', password='test')

        self.assertEqual(user.role, User.Role.SUPER_ADMIN)
        self.assertIsNone(user.tenant)
