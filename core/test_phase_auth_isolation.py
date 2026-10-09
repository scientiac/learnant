from django.test import TestCase
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, Tenant, User


class PhaseAuthorizationIsolationReviewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.other_tenant = Tenant.objects.create(name='Tenant B')
        self.tenant_admin = User.objects.create_user(
            username='tenant-admin', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.other_admin = User.objects.create_user(
            username='other-admin', password='test', role=User.Role.TENANT_ADMIN, tenant=self.other_tenant
        )
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant,
            must_change_password=False,
        )
        self.viewer = User.objects.create_user(username='viewer', password='test', role=User.Role.SUPER_VIEWER)
        self.admin = User.objects.create_user(username='admin', password='test', role=User.Role.ADMIN)
        self.course = Course.objects.create(tenant=self.tenant, title='Course A', creator=self.tenant_admin)
        self.other_course = Course.objects.create(
            tenant=self.other_tenant, title='Course B', creator=self.other_admin
        )
        self.lesson = Lesson.objects.create(course=self.course, title='Lesson A', content='Content', order=1)
        self.assignment = CourseAssignment.objects.create(
            tenant=self.tenant, course=self.course, learner=self.learner
        )

    def test_anonymous_users_redirect_from_protected_pages(self):
        protected_urls = [
            reverse('dashboard'),
            reverse('course-list'),
            reverse('course-create'),
            reverse('lesson-list', args=[self.course.id]),
            reverse('assignment-list', args=[self.course.id]),
            reverse('progress-list', args=[self.course.id]),
            reverse('tenant-list'),
        ]

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse('login'), response['Location'])

    def test_tenant_roles_cannot_access_platform_tenant_list(self):
        self.client.login(username='tenant-admin', password='test')
        tenant_admin_response = self.client.get(reverse('tenant-list'))
        self.client.logout()
        self.client.login(username='learner', password='test')
        learner_response = self.client.get(reverse('tenant-list'))

        self.assertEqual(tenant_admin_response.status_code, 403)
        self.assertEqual(learner_response.status_code, 403)

    def test_platform_viewer_is_read_only_for_tenant_learning_records(self):
        self.client.login(username='viewer', password='test')

        responses = [
            self.client.post(reverse('course-create'), {'title': 'Viewer Course'}),
            self.client.post(reverse('course-update', args=[self.course.id]), {'title': 'Viewer Update'}),
            self.client.post(reverse('course-delete', args=[self.course.id])),
            self.client.post(
                reverse('lesson-update', args=[self.course.id, self.lesson.id]),
                {'title': 'Viewer Lesson', 'content': 'Nope', 'order': 1},
            ),
            self.client.post(reverse('assignment-create', args=[self.course.id]), {'learner': self.learner.id}),
        ]

        self.assertTrue(all(response.status_code == 403 for response in responses))
        self.assertFalse(Course.objects.filter(title='Viewer Course').exists())

    def test_admin_can_read_platform_but_cannot_reactivate_tenant(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='admin', password='test')

        list_response = self.client.get(reverse('tenant-list'))
        reactivate_response = self.client.post(reverse('tenant-reactivate', args=[self.tenant.id]))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(reactivate_response.status_code, 403)

    def test_tenant_admin_cross_tenant_mutation_urls_return_404(self):
        self.client.login(username='tenant-admin', password='test')

        responses = [
            self.client.post(
                reverse('course-update', args=[self.other_course.id]),
                {'title': 'Nope', 'description': ''},
            ),
            self.client.post(reverse('course-delete', args=[self.other_course.id])),
            self.client.post(
                reverse('lesson-create', args=[self.other_course.id]),
                {'title': 'Nope', 'content': 'Nope', 'order': 1},
            ),
            self.client.post(
                reverse('assignment-create', args=[self.other_course.id]),
                {'learner': self.learner.id},
            ),
            self.client.get(reverse('progress-list', args=[self.other_course.id])),
        ]

        self.assertTrue(all(response.status_code == 404 for response in responses))

    def test_django_admin_requires_staff_access(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
