from django.test import TestCase
from django.urls import reverse

from .models import Course, Tenant, User


class CourseAssistantPreviewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Institute A')
        self.tenant_admin = User.objects.create_user(
            username='manager', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant
        )
        self.viewer = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('course-assistant-preview'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_tenant_admin_can_preview_static_outline_without_creating_course(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('course-assistant-preview'),
            {
                'learner_role': 'Junior analyst',
                'current_level': 'beginner',
                'goal': 'Build a reporting dashboard',
                'hours_per_week': '5',
                'duration_weeks': '8',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Static preview')
        self.assertContains(response, 'Junior analyst')
        self.assertContains(response, 'Build a reporting dashboard')
        self.assertContains(response, 'Weeks 1–2')
        self.assertEqual(len(response.context['preview']['modules']), 4)
        self.assertFalse(Course.objects.exists())

    def test_non_tenant_admin_roles_are_denied(self):
        for user in (self.learner, self.viewer):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse('course-assistant-preview'))
                self.assertEqual(response.status_code, 403)
                self.client.logout()

    def test_invalid_preview_values_do_not_render_sample_output(self):
        self.client.login(username='manager', password='test')

        response = self.client.post(
            reverse('course-assistant-preview'),
            {
                'learner_role': 'Analyst',
                'current_level': 'expert',
                'goal': 'Learn',
                'hours_per_week': '0',
                'duration_weeks': '80',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['preview'])
        self.assertFalse(Course.objects.exists())
