from django.test import TestCase
from django.urls import reverse

from .models import Tenant, User


class TenantUserManagementTests(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Institute A')
        self.tenant_b = Tenant.objects.create(name='Institute B')
        self.admin_a = User.objects.create_user(
            username='manager-a', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant_a
        )
        self.admin_b = User.objects.create_user(
            username='manager-b', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant_b
        )
        self.learner_a = User.objects.create_user(
            username='learner-a', password='test', role=User.Role.TENANT_USER,
            tenant=self.tenant_a, must_change_password=False,
        )
        self.learner_b = User.objects.create_user(
            username='learner-b', password='test', role=User.Role.TENANT_USER,
            tenant=self.tenant_b, must_change_password=False,
        )
        self.platform_admin = User.objects.create_user(
            username='platform-admin', password='test', role=User.Role.ADMIN
        )
        self.viewer = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )

    def test_tenant_admin_lists_only_own_tenant_learners(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.get(reverse('tenant-user-list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'learner-a')
        self.assertNotContains(response, 'learner-b')

    def test_tenant_admin_can_edit_and_deactivate_own_learner_without_escalation(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.post(
            reverse('tenant-user-update', args=[self.learner_a.id]),
            {
                'first_name': 'Updated',
                'last_name': 'Learner',
                'email': 'updated@example.test',
                'is_active': '',
                'role': User.Role.SUPER_ADMIN,
                'tenant': self.tenant_b.id,
            },
        )
        self.learner_a.refresh_from_db()

        self.assertRedirects(response, reverse('tenant-user-list'))
        self.assertEqual(self.learner_a.first_name, 'Updated')
        self.assertEqual(self.learner_a.email, 'updated@example.test')
        self.assertFalse(self.learner_a.is_active)
        self.assertEqual(self.learner_a.role, User.Role.TENANT_USER)
        self.assertEqual(self.learner_a.tenant, self.tenant_a)

    def test_tenant_admin_cannot_edit_another_tenant_user_by_id(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.post(
            reverse('tenant-user-update', args=[self.learner_b.id]),
            {'first_name': 'Hijacked', 'last_name': '', 'email': '', 'is_active': 'on'},
        )

        self.assertEqual(response.status_code, 404)
        self.learner_b.refresh_from_db()
        self.assertEqual(self.learner_b.first_name, '')
        self.assertTrue(self.learner_b.is_active)

    def test_platform_admin_can_manage_selected_tenant_roster(self):
        self.client.login(username='platform-admin', password='test')

        list_response = self.client.get(reverse('platform-tenant-users', args=[self.tenant_b.id]))
        update_response = self.client.post(
            reverse('platform-tenant-user-update', args=[self.tenant_b.id, self.learner_b.id]),
            {'first_name': 'Platform Edited', 'last_name': 'Learner', 'email': '', 'is_active': 'on'},
        )
        self.learner_b.refresh_from_db()

        self.assertContains(list_response, 'learner-b')
        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(self.learner_b.first_name, 'Platform Edited')
        self.assertEqual(self.learner_b.tenant, self.tenant_b)

    def test_superviewer_can_read_but_not_edit_platform_tenant_roster(self):
        self.client.login(username='viewer', password='test')

        response = self.client.get(reverse('platform-tenant-users', args=[self.tenant_a.id]))
        update_response = self.client.post(
            reverse('platform-tenant-user-update', args=[self.tenant_a.id, self.learner_a.id]),
            {'first_name': 'Viewer Edit', 'last_name': '', 'email': '', 'is_active': 'on'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'manager-a')
        self.assertContains(response, 'learner-a')
        self.assertEqual(update_response.status_code, 403)

    def test_expired_tenant_roster_is_read_only(self):
        self.tenant_a.status = Tenant.Status.EXPIRED
        self.tenant_a.save()
        self.client.login(username='manager-a', password='test')

        list_response = self.client.get(reverse('tenant-user-list'))
        update_response = self.client.post(
            reverse('tenant-user-update', args=[self.learner_a.id]),
            {'first_name': 'No edit', 'last_name': '', 'email': '', 'is_active': ''},
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'learner-a')
        self.assertEqual(update_response.status_code, 403)
