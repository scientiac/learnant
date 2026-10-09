from django.test import TestCase
from django.utils import timezone

from .models import Tenant, User
from .permissions import (
    can_manage_platform,
    can_mutate_tenant_data,
    can_reactivate_tenant,
    can_read_platform,
    can_read_tenant_data,
    can_use_tenant_request_method,
)


class PermissionHelperTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.other_tenant = Tenant.objects.create(name='Tenant B')
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
        self.super_viewer = User.objects.create_user(
            username='super-viewer',
            password='test',
            role=User.Role.SUPER_VIEWER,
        )
        self.tenant_admin = User.objects.create_user(
            username='tenant-admin',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.tenant,
        )
        self.tenant_user = User.objects.create_user(
            username='tenant-user',
            password='test',
            role=User.Role.TENANT_USER,
            tenant=self.tenant,
        )

    def test_platform_read_access_includes_super_viewer(self):
        self.assertTrue(can_read_platform(self.super_admin))
        self.assertTrue(can_read_platform(self.admin))
        self.assertTrue(can_read_platform(self.super_viewer))
        self.assertFalse(can_read_platform(self.tenant_admin))

    def test_platform_management_excludes_super_viewer(self):
        self.assertTrue(can_manage_platform(self.super_admin))
        self.assertTrue(can_manage_platform(self.admin))
        self.assertFalse(can_manage_platform(self.super_viewer))
        self.assertFalse(can_manage_platform(self.tenant_user))

    def test_only_super_admin_can_reactivate_tenant(self):
        self.assertTrue(can_reactivate_tenant(self.super_admin))
        self.assertFalse(can_reactivate_tenant(self.admin))
        self.assertFalse(can_reactivate_tenant(self.super_viewer))
        self.assertFalse(can_reactivate_tenant(self.tenant_admin))

    def test_tenant_users_read_only_own_tenant_data(self):
        self.assertTrue(can_read_tenant_data(self.tenant_admin, self.tenant))
        self.assertTrue(can_read_tenant_data(self.tenant_user, self.tenant))
        self.assertFalse(can_read_tenant_data(self.tenant_admin, self.other_tenant))
        self.assertFalse(can_read_tenant_data(self.tenant_user, self.other_tenant))

    def test_platform_users_can_read_tenant_data(self):
        self.assertTrue(can_read_tenant_data(self.super_admin, self.tenant))
        self.assertTrue(can_read_tenant_data(self.admin, self.tenant))
        self.assertTrue(can_read_tenant_data(self.super_viewer, self.tenant))

    def test_active_tenant_users_can_mutate_tenant_data(self):
        self.assertTrue(can_mutate_tenant_data(self.tenant_admin))
        self.assertTrue(can_mutate_tenant_data(self.tenant_user))
        self.assertFalse(can_mutate_tenant_data(self.super_admin))

    def test_expired_tenant_users_can_read_but_not_mutate(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.trial_ends_at = timezone.now()
        self.tenant.save()
        self.tenant_admin.refresh_from_db()
        self.tenant_user.refresh_from_db()

        self.assertTrue(can_read_tenant_data(self.tenant_admin, self.tenant))
        self.assertTrue(can_use_tenant_request_method(self.tenant_admin, 'GET'))
        self.assertFalse(can_mutate_tenant_data(self.tenant_admin))
        self.assertFalse(can_use_tenant_request_method(self.tenant_admin, 'POST'))
        self.assertFalse(can_use_tenant_request_method(self.tenant_user, 'PATCH'))
