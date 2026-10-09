from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, Tenant, User


class WebFlowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Demo Institute')
        self.learner = User.objects.create_user(
            username='learner',
            password='password123',
            role=User.Role.TENANT_USER,
            tenant=self.tenant,
            must_change_password=False,
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
        self.assertContains(response, '<link rel="icon" type="image/svg+xml"')
        self.assertGreaterEqual(response.content.count(b'<svg'), 2)
        self.assertNotContains(response, '🐜 Learnant')

    def test_about_page_explains_product_and_production_access_without_demo_credentials(self):
        response = self.client.get(reverse('about'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'How Learnant works')
        self.assertContains(response, 'Create courses and lessons')
        self.assertContains(response, 'Workspace roles')
        self.assertContains(response, 'Learnant does not provide shared demo or evaluation accounts in production.')
        self.assertNotContains(response, 'Demo Evaluation Accounts')
        self.assertNotContains(response, 'password123')

    def test_authenticated_home_redirects_to_dashboard(self):
        self.client.login(username='learner', password='password123')

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('dashboard'))

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Log in')

    def test_authenticated_header_account_menu_links_profile_and_post_logout(self):
        self.client.login(username='learner', password='password123')

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, '<summary', html=False)
        self.assertContains(response, '@learner')
        self.assertContains(response, reverse('profile-settings'))
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertNotContains(response, '>Profile</a>')
        self.assertLess(response.content.index(b'>Courses</a>'), response.content.index(b'@learner'))
        self.assertContains(response, 'btn btn-outline mb-1 w-full justify-start')
        self.assertContains(response, 'btn btn-outline w-full justify-start')
        self.assertContains(response, 'var(--destructive)')

    def test_learner_can_login_and_view_tenant_dashboard(self):
        logged_in = self.client.login(username='learner', password='password123')

        self.assertTrue(logged_in)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Demo Institute')
        self.assertContains(response, 'Tenant User')
        self.assertContains(response, 'Open courses')
        self.assertContains(response, 'Your learning path')
        self.assertContains(response, 'No course has been assigned yet')

    def test_tenant_admin_dashboard_shows_actionable_setup_checklist(self):
        self.learner.delete()
        tenant_admin = User.objects.create_user(
            username='manager', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.client.login(username='manager', password='test')

        new_colony_response = self.client.get(reverse('dashboard'))
        self.assertContains(new_colony_response, 'Set up your colony')
        self.assertContains(new_colony_response, 'Create your first course')
        self.assertContains(new_colony_response, reverse('course-create'))

        course = Course.objects.create(tenant=self.tenant, title='First Course', creator=tenant_admin)
        course_response = self.client.get(reverse('dashboard'))
        self.assertNotContains(course_response, 'Create your first course')
        self.assertContains(course_response, 'Add your first lesson')
        self.assertContains(course_response, reverse('lesson-create', args=[course.id]))

        Lesson.objects.create(course=course, title='First Lesson', content='Read this', order=1)
        learner_step_response = self.client.get(reverse('dashboard'))
        self.assertNotContains(learner_step_response, 'Add your first lesson')
        self.assertContains(learner_step_response, reverse('bulk-student-add'))
        self.assertContains(learner_step_response, 'Onboard your first learner')

        User.objects.create_user(
            username='first-learner',
            password='test',
            role=User.Role.TENANT_USER,
            tenant=self.tenant,
        )
        completed_response = self.client.get(reverse('dashboard'))
        self.assertNotContains(completed_response, 'Set up your colony')

    def test_assigned_learner_dashboard_links_to_assigned_syllabus(self):
        tenant_admin = User.objects.create_user(
            username='manager', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        course = Course.objects.create(tenant=self.tenant, title='Assigned Course', creator=tenant_admin)
        lesson = Lesson.objects.create(
            course=course, title='First Study Lesson', content='Welcome!', order=1
        )
        CourseAssignment.objects.create(tenant=self.tenant, course=course, learner=self.learner)
        self.client.login(username='learner', password='password123')

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Your learning path')
        self.assertContains(response, 'Start First Study Lesson')
        self.assertContains(response, reverse('lesson-detail', args=[course.id, lesson.id]))

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
        self.assertFalse(User.objects.get(username='learner').must_change_password)
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
        self.assertContains(response, 'Admin email')

    def test_signup_creates_tenant_and_admin(self):
        response = self.client.post(reverse('signup'), {
            'org_name': 'New Test Institute',
            'username': 'newadmin',
            'email': 'newadmin@example.test',
            'password1': 'Str0ng!Pass99',
            'password2': 'Str0ng!Pass99',
        })

        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='newadmin').exists())
        self.assertTrue(Tenant.objects.filter(name='New Test Institute').exists())
        user = User.objects.get(username='newadmin')
        self.assertEqual(user.role, User.Role.TENANT_ADMIN)
        self.assertEqual(user.tenant.name, 'New Test Institute')
        self.assertEqual(user.email, 'newadmin@example.test')

    def test_signup_rejects_duplicate_org_name(self):
        Tenant.objects.create(name='Existing Org')
        response = self.client.post(reverse('signup'), {
            'org_name': 'Existing Org',
            'username': 'someone',
            'email': 'someone@example.test',
            'password1': 'Str0ng!Pass99',
            'password2': 'Str0ng!Pass99',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    def test_signup_rejects_password_mismatch(self):
        response = self.client.post(reverse('signup'), {
            'org_name': 'Mismatch Org',
            'username': 'mismatchuser',
            'email': 'mismatch@example.test',
            'password1': 'Str0ng!Pass99',
            'password2': 'WrongPass99!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')

    def test_authenticated_user_signup_redirects(self):
        self.client.login(username='learner', password='password123')
        response = self.client.get(reverse('signup'))

        self.assertRedirects(response, reverse('dashboard'))
