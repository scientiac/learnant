from django.test import TestCase
from django.urls import reverse

from .models import Tenant, User


class OrganizationSettingsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Institute A')
        self.other_tenant = Tenant.objects.create(name='Institute B')
        self.tenant_admin = User.objects.create_user(
            username='manager', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.other_admin = User.objects.create_user(
            username='other-manager', password='test', role=User.Role.TENANT_ADMIN, tenant=self.other_tenant
        )
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant
        )

    def test_anonymous_user_cannot_open_organization_settings(self):
        response = self.client.get(reverse('organization-settings'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_tenant_admin_can_update_own_organization_settings(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('organization-settings'),
            {'name': 'Institute A Updated', 'brand_color': '#123456', 'tenant': self.other_tenant.id},
        )
        self.tenant.refresh_from_db()
        self.other_tenant.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.tenant.name, 'Institute A Updated')
        self.assertEqual(self.tenant.brand_color, '#123456')
        self.assertEqual(self.other_tenant.name, 'Institute B')

    def test_other_roles_cannot_update_organization_settings(self):
        self.client.login(username='learner', password='test')

        response = self.client.post(
            reverse('organization-settings'), {'name': 'Learner Rename', 'brand_color': '#ffffff'}
        )

        self.assertEqual(response.status_code, 403)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.name, 'Institute A')

    def test_expired_tenant_is_read_only_for_organization_settings(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('organization-settings'), {'name': 'Expired Rename', 'brand_color': '#ffffff'}
        )

        self.assertEqual(response.status_code, 403)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.name, 'Institute A')

    def test_invalid_brand_color_is_rejected(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('organization-settings'), {'name': 'Institute A', 'brand_color': 'red'}
        )

        self.assertEqual(response.status_code, 200)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.brand_color, '#09090b')


class ProfileSettingsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Institute A')
        self.other_tenant = Tenant.objects.create(name='Institute B')
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant
        )
        self.platform_user = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )

    def test_anonymous_user_cannot_open_profile_settings(self):
        response = self.client.get(reverse('profile-settings'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_user_can_update_own_profile_but_not_role_or_tenant(self):
        self.client.login(username='learner', password='test')

        response = self.client.post(
            reverse('profile-settings'),
            {
                'first_name': 'Learner',
                'last_name': 'One',
                'email': 'learner@example.test',
                'role': User.Role.SUPER_ADMIN,
                'tenant': self.other_tenant.id,
            },
        )
        self.learner.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.learner.first_name, 'Learner')
        self.assertEqual(self.learner.email, 'learner@example.test')
        self.assertEqual(self.learner.role, User.Role.TENANT_USER)
        self.assertEqual(self.learner.tenant, self.tenant)

    def test_platform_user_can_update_own_profile(self):
        self.client.login(username='viewer', password='test')

        response = self.client.post(
            reverse('profile-settings'),
            {'first_name': 'Audit', 'last_name': 'Viewer', 'email': 'viewer@example.test'},
        )
        self.platform_user.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.platform_user.first_name, 'Audit')
        self.assertIsNone(self.platform_user.tenant)
        self.assertEqual(self.platform_user.role, User.Role.SUPER_VIEWER)

    def test_expired_tenant_user_cannot_update_profile(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='learner', password='test')

        response = self.client.post(
            reverse('profile-settings'),
            {'first_name': 'Changed', 'last_name': '', 'email': ''},
        )

        self.assertEqual(response.status_code, 403)
        self.learner.refresh_from_db()
        self.assertEqual(self.learner.first_name, '')
