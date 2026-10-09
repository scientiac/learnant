from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse

from .models import Tenant, User


class WebFlowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Demo Institute')
        self.learner = User.objects.create_user(
            username='learner',
            password='password123',
            role=User.Role.TENANT_USER,
            tenant=self.tenant,
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            password='password123',
            role=User.Role.SUPER_VIEWER,
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Log in')

    def test_learner_can_login_and_view_tenant_dashboard(self):
        logged_in = self.client.login(username='learner', password='password123')

        self.assertTrue(logged_in)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Demo Institute')
        self.assertContains(response, 'Tenant User')

    def test_super_viewer_dashboard_is_read_only(self):
        self.client.login(username='viewer', password='password123')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Platform overview')
        self.assertContains(response, 'Platform management: read-only')

    def test_health_check_stays_public(self):
        response = self.client.get(reverse('health-check'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_seed_demo_creates_login_users(self):
        call_command('seed_demo', verbosity=0)

        self.assertTrue(self.client.login(username='learner', password='password123'))
        self.assertTrue(User.objects.filter(username='superadmin').exists())
