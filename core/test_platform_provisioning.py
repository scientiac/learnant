import os
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import Tenant, User


class PlatformBootstrapTests(TestCase):
    def bootstrap_env(self, **overrides):
        values = {
            'LEARNANT_SUPERADMIN_USERNAME': 'deployment-owner',
            'LEARNANT_SUPERADMIN_EMAIL': 'owner@example.test',
            'LEARNANT_SUPERADMIN_PASSWORD': 'UniqueStrong!Password874',
        }
        values.update(overrides)
        return patch.dict(os.environ, values, clear=False)

    def test_bootstrap_command_creates_forced_reset_superadmin_and_is_idempotent(self):
        with self.bootstrap_env():
            call_command('bootstrap_superadmin', verbosity=0)
            account = User.objects.get(username='deployment-owner')
            self.assertEqual(account.role, User.Role.SUPER_ADMIN)
            self.assertIsNone(account.tenant)
            self.assertTrue(account.is_staff)
            self.assertTrue(account.is_superuser)
            self.assertTrue(account.must_change_password)
            self.assertTrue(account.check_password('UniqueStrong!Password874'))

            call_command('bootstrap_superadmin', verbosity=0)
            self.assertEqual(User.objects.filter(username='deployment-owner').count(), 1)
            self.assertTrue(User.objects.get(username='deployment-owner').must_change_password)

    def test_bootstrap_refuses_to_promote_an_existing_non_superadmin(self):
        User.objects.create_user(username='deployment-owner', password='test', role=User.Role.ADMIN)
        with self.bootstrap_env(), self.assertRaises(CommandError):
            call_command('bootstrap_superadmin', verbosity=0)

    def test_bootstrap_requires_all_secret_environment_values(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(CommandError):
            call_command('bootstrap_superadmin', verbosity=0)


class PlatformAccountProvisioningTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.super_admin = User.objects.create_user(
            username='root', password='test', role=User.Role.SUPER_ADMIN
        )
        self.admin = User.objects.create_user(
            username='admin', password='test', role=User.Role.ADMIN
        )
        self.viewer = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )

    def test_superadmin_can_provision_single_admin_or_superviewer_with_reset_required(self):
        self.client.login(username='root', password='test')
        for username, role in (
            ('new-admin', User.Role.ADMIN),
            ('new-viewer', User.Role.SUPER_VIEWER),
        ):
            with self.subTest(role=role):
                response = self.client.post(
                    reverse('platform-account-create'),
                    {
                        'username': username,
                        'email': f'{username}@example.test',
                        'first_name': 'Platform',
                        'last_name': 'Staff',
                        'role': role,
                    },
                )
                account = User.objects.get(username=username)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(account.role, role)
                self.assertIsNone(account.tenant)
                self.assertTrue(account.must_change_password)
                self.assertTrue(account.check_password(response.context['created_account']['password']))

    def test_only_superadmin_can_provision_platform_roles(self):
        for user in (self.admin, self.viewer):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse('platform-account-create'))
                self.assertEqual(response.status_code, 403)
                self.client.logout()

    def test_platform_account_form_cannot_grant_superadmin(self):
        self.client.login(username='root', password='test')

        response = self.client.post(
            reverse('platform-account-create'),
            {
                'username': 'attempted-root',
                'email': 'attempted-root@example.test',
                'role': User.Role.SUPER_ADMIN,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='attempted-root').exists())


class PlatformTenantCreationTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='root', password='test', role=User.Role.SUPER_ADMIN
        )
        self.admin = User.objects.create_user(
            username='admin', password='test', role=User.Role.ADMIN
        )
        self.viewer = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )

    def test_admin_can_create_tenant_and_initial_tenant_admin(self):
        self.client.login(username='admin', password='test')

        response = self.client.post(
            reverse('platform-tenant-create'),
            {
                'org_name': 'Platform Created Institute',
                'username': 'initial-manager',
                'email': 'manager@example.test',
                'password1': 'Strong!ManagerPassword881',
                'password2': 'Strong!ManagerPassword881',
            },
        )

        self.assertRedirects(response, reverse('tenant-list'))
        manager = User.objects.get(username='initial-manager')
        self.assertEqual(manager.role, User.Role.TENANT_ADMIN)
        self.assertFalse(manager.must_change_password)
        self.assertEqual(manager.tenant.name, 'Platform Created Institute')

    def test_superviewer_cannot_create_tenant(self):
        self.client.login(username='viewer', password='test')

        response = self.client.post(reverse('platform-tenant-create'), {})

        self.assertEqual(response.status_code, 403)
