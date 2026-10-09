from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Course, Tenant, User
from .permissions import can_mutate_tenant_data


class TrialExpirationTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.tenant = Tenant.objects.create(
            name='Tenant A',
            trial_starts_at=self.now - timedelta(days=14),
            trial_ends_at=self.now + timedelta(hours=1),
        )
        self.tenant_admin = User.objects.create_user(
            username='tenant-admin',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.tenant,
        )
        self.super_admin = User.objects.create_user(
            username='super-admin',
            password='test',
            role=User.Role.SUPER_ADMIN,
        )
        self.admin = User.objects.create_user(
            username='admin',
            password='test',
            role=User.Role.ADMIN,
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            password='test',
            role=User.Role.SUPER_VIEWER,
        )

    def test_can_mutate_denies_at_trial_boundary(self):
        self.tenant.trial_ends_at = timezone.now()
        self.tenant.save()
        self.tenant_admin.refresh_from_db()

        self.assertFalse(can_mutate_tenant_data(self.tenant_admin))

    def test_expire_trials_command_is_idempotent_and_preserves_data(self):
        Course.objects.create(tenant=self.tenant, title='Existing Course', creator=self.tenant_admin)
        self.tenant.trial_ends_at = timezone.now() - timedelta(seconds=1)
        self.tenant.save()

        call_command('expire_trials', verbosity=0)
        self.tenant.refresh_from_db()
        first_expired_at = self.tenant.expired_at
        call_command('expire_trials', verbosity=0)
        self.tenant.refresh_from_db()

        self.assertEqual(self.tenant.status, Tenant.Status.EXPIRED)
        self.assertEqual(self.tenant.expired_at, first_expired_at)
        self.assertTrue(Course.objects.filter(title='Existing Course', tenant=self.tenant).exists())

    def test_request_time_expired_tenant_cannot_create_course(self):
        self.tenant.trial_ends_at = timezone.now() - timedelta(seconds=1)
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('course-create'), {'title': 'Late Course'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Course.objects.filter(title='Late Course').exists())

    def test_super_admin_can_reactivate_expired_tenant(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.expired_at = timezone.now()
        self.tenant.save()
        self.client.login(username='super-admin', password='test')

        response = self.client.post(reverse('tenant-reactivate', args=[self.tenant.id]))
        self.tenant.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.tenant.status, Tenant.Status.ACTIVE)
        self.assertIsNone(self.tenant.expired_at)
        self.assertGreater(self.tenant.trial_ends_at, timezone.now())

    def test_admin_cannot_reactivate_tenant(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.expired_at = timezone.now()
        self.tenant.save()
        self.client.login(username='admin', password='test')

        response = self.client.post(reverse('tenant-reactivate', args=[self.tenant.id]))
        self.tenant.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.tenant.status, Tenant.Status.EXPIRED)

    def test_super_viewer_can_read_tenant_list_but_cannot_reactivate(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.expired_at = timezone.now()
        self.tenant.save()
        self.client.login(username='viewer', password='test')

        list_response = self.client.get(reverse('tenant-list'))
        reactivate_response = self.client.post(reverse('tenant-reactivate', args=[self.tenant.id]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.tenant.name)
        self.assertEqual(reactivate_response.status_code, 403)
