from django.test import TestCase
from django.urls import reverse

from .models import Tenant, User


class BulkStudentOnboardingTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Institute A')
        self.other_tenant = Tenant.objects.create(name='Institute B')
        self.tenant_admin = User.objects.create_user(
            username='manager', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.other_learner = User.objects.create_user(
            username='existing_student', password='test', role=User.Role.TENANT_USER,
            tenant=self.other_tenant, must_change_password=False,
        )
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant,
            must_change_password=False,
        )
        self.viewer = User.objects.create_user(username='viewer', password='test', role=User.Role.SUPER_VIEWER)

    def test_anonymous_request_redirects_to_login(self):
        response = self.client.get(reverse('bulk-student-add'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_tenant_admin_creates_username_and_email_learners_in_own_tenant(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('bulk-student-add'),
            {
                'students': 'new_student\nnew.student@example.test',
                'tenant': self.other_tenant.id,
                'role': User.Role.SUPER_ADMIN,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['created_students']), 2)
        first = User.objects.get(username='new_student')
        second = User.objects.get(email='new.student@example.test')
        for learner in (first, second):
            self.assertEqual(learner.tenant, self.tenant)
            self.assertEqual(learner.role, User.Role.TENANT_USER)
            self.assertTrue(learner.must_change_password)
            self.assertTrue(learner.check_password(
                next(row['password'] for row in response.context['created_students'] if row['username'] == learner.username)
            ))

    def test_tenant_admin_cannot_reuse_another_tenant_username(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('bulk-student-add'), {'students': 'existing_student\nnew_student'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['created_students'], [])
        self.assertFalse(User.objects.filter(username='new_student').exists())
        self.assertContains(response, 'already in use')

    def test_duplicate_entries_are_rejected_without_partial_creation(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('bulk-student-add'), {'students': 'same_user\nsame_user'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='same_user').exists())
        self.assertContains(response, 'duplicate entry')

    def test_non_tenant_admin_cannot_bulk_onboard(self):
        self.client.login(username='learner', password='test')

        response = self.client.post(reverse('bulk-student-add'), {'students': 'new_student'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='new_student').exists())

    def test_platform_viewer_cannot_bulk_onboard(self):
        self.client.login(username='viewer', password='test')

        response = self.client.post(reverse('bulk-student-add'), {'students': 'new_student'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='new_student').exists())

    def test_expired_tenant_admin_cannot_bulk_onboard(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='manager', password='test')

        response = self.client.post(reverse('bulk-student-add'), {'students': 'new_student'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='new_student').exists())

    def test_batch_is_limited_to_100_students(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('bulk-student-add'), {'students': '\n'.join(f'student{i}' for i in range(101))}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username__startswith='student').exists())
        self.assertContains(response, 'at most 100')
