from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Course, Tenant, User


class CourseModelTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.other_tenant = Tenant.objects.create(name='Tenant B')
        self.tenant_admin = User.objects.create_user(
            username='tenant-admin',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.tenant,
        )
        self.learner = User.objects.create_user(
            username='learner',
            password='test',
            role=User.Role.TENANT_USER,
            tenant=self.tenant,
        )

    def test_course_creator_must_match_tenant(self):
        course = Course(
            tenant=self.other_tenant,
            title='Cross Tenant Course',
            creator=self.tenant_admin,
        )

        with self.assertRaises(ValidationError):
            course.full_clean()

    def test_learner_cannot_create_course(self):
        course = Course(tenant=self.tenant, title='Learner Course', creator=self.learner)

        with self.assertRaises(ValidationError):
            course.full_clean()


class CourseListViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.other_tenant = Tenant.objects.create(name='Tenant B')
        self.tenant_admin = User.objects.create_user(
            username='tenant-admin',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.tenant,
        )
        self.other_admin = User.objects.create_user(
            username='other-admin',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.other_tenant,
        )
        self.learner = User.objects.create_user(
            username='learner',
            password='test',
            role=User.Role.TENANT_USER,
            tenant=self.tenant,
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            password='test',
            role=User.Role.SUPER_VIEWER,
        )
        self.course = Course.objects.create(
            tenant=self.tenant,
            title='Tenant A Course',
            creator=self.tenant_admin,
        )
        self.other_course = Course.objects.create(
            tenant=self.other_tenant,
            title='Tenant B Course',
            creator=self.other_admin,
        )

    def test_course_list_requires_login(self):
        response = self.client.get(reverse('course-list'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_tenant_admin_sees_only_own_tenant_courses(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.get(reverse('course-list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertNotContains(response, self.other_course.title)

    def test_learner_does_not_see_unassigned_courses_yet(self):
        self.client.login(username='learner', password='test')

        response = self.client.get(reverse('course-list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.course.title)
        self.assertContains(response, 'No courses are available')

    def test_super_viewer_can_read_all_courses(self):
        self.client.login(username='viewer', password='test')

        response = self.client.get(reverse('course-list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, self.other_course.title)
