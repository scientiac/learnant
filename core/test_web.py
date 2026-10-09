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

    def test_public_home_is_informative_and_links_to_signin_and_org_signup(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A secure learning workspace for every institute')
        self.assertContains(response, 'isolated')
        self.assertContains(response, reverse('login'))
        self.assertContains(response, reverse('signup'))
        self.assertContains(response, 'Sign up your organization here')
        self.assertContains(response, 'Seeded demo accounts')

    def test_authenticated_home_redirects_to_dashboard(self):
        self.client.login(username='learner', password='password123')

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('dashboard'))

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
        self.assertContains(response, 'Open courses')

    def test_super_viewer_dashboard_is_read_only(self):
        self.client.login(username='viewer', password='password123')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Tenants')
        self.assertContains(response, 'Read-only')
        self.assertContains(response, 'View tenants')

    def test_health_check_stays_public(self):
        response = self.client.get(reverse('health-check'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_seed_demo_creates_login_users(self):
        call_command('seed_demo', verbosity=0)

        self.assertTrue(self.client.login(username='learner', password='password123'))
        self.assertTrue(User.objects.filter(username='superadmin').exists())
        self.client.logout()
        for username in ('tenant_admin', 'institute_admin'):
            with self.subTest(username=username):
                self.assertTrue(self.client.login(username=username, password='password123'))
                user = User.objects.get(username=username)
                self.assertEqual(user.role, User.Role.TENANT_ADMIN)
                self.assertEqual(user.tenant.name, 'Demo Institute')
                self.client.logout()

    def test_signup_page_loads(self):
        response = self.client.get(reverse('signup'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create your organization colony')
        self.assertContains(response, 'Learners join through their institute')

    def test_signup_creates_tenant_and_admin(self):
        response = self.client.post(reverse('signup'), {
            'org_name': 'New Test Institute',
            'username': 'newadmin',
            'password1': 'Str0ng!Pass99',
            'password2': 'Str0ng!Pass99',
        })

        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='newadmin').exists())
        self.assertTrue(Tenant.objects.filter(name='New Test Institute').exists())
        user = User.objects.get(username='newadmin')
        self.assertEqual(user.role, User.Role.TENANT_ADMIN)
        self.assertEqual(user.tenant.name, 'New Test Institute')

    def test_signup_rejects_duplicate_org_name(self):
        Tenant.objects.create(name='Existing Org')
        response = self.client.post(reverse('signup'), {
            'org_name': 'Existing Org',
            'username': 'someone',
            'password1': 'Str0ng!Pass99',
            'password2': 'Str0ng!Pass99',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    def test_signup_rejects_password_mismatch(self):
        response = self.client.post(reverse('signup'), {
            'org_name': 'Mismatch Org',
            'username': 'mismatchuser',
            'password1': 'Str0ng!Pass99',
            'password2': 'WrongPass99!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')

    def test_authenticated_user_signup_redirects(self):
        self.client.login(username='learner', password='password123')
        response = self.client.get(reverse('signup'))

        self.assertRedirects(response, reverse('dashboard'))
