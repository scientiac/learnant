from django.test import TestCase
from django.urls import reverse

from .models import Course, Lesson, Tenant, User


class LessonViewTests(TestCase):
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
        self.lesson = Lesson.objects.create(
            course=self.course,
            title='Tenant A Lesson',
            content='Tenant A content',
            order=1,
        )
        self.other_lesson = Lesson.objects.create(
            course=self.other_course,
            title='Tenant B Lesson',
            content='Tenant B content',
            order=1,
        )

    def test_lesson_list_requires_login(self):
        response = self.client.get(reverse('lesson-list', args=[self.course.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_tenant_admin_sees_own_course_lessons(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.get(reverse('lesson-list', args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lesson.title)
        self.assertNotContains(response, self.other_lesson.title)

    def test_tenant_admin_cannot_access_other_tenant_course_lessons(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.get(reverse('lesson-list', args=[self.other_course.id]))

        self.assertEqual(response.status_code, 404)

    def test_super_viewer_can_read_lessons(self):
        self.client.login(username='viewer', password='test')

        response = self.client.get(reverse('lesson-list', args=[self.other_course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.other_lesson.title)

    def test_learner_cannot_access_unassigned_course_lessons_yet(self):
        self.client.login(username='learner', password='test')

        response = self.client.get(reverse('lesson-list', args=[self.course.id]))

        self.assertEqual(response.status_code, 404)

    def test_active_tenant_admin_can_create_lesson(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-create', args=[self.course.id]),
            {'title': 'New Lesson', 'content': 'New content', 'order': 2},
        )

        self.assertEqual(response.status_code, 302)
        lesson = Lesson.objects.get(title='New Lesson')
        self.assertEqual(lesson.course, self.course)

    def test_posted_course_id_is_ignored_when_creating_lesson(self):
        self.client.login(username='tenant-admin', password='test')

        self.client.post(
            reverse('lesson-create', args=[self.course.id]),
            {
                'title': 'Course Spoof Attempt',
                'content': 'Should stay on URL course',
                'order': 3,
                'course': self.other_course.id,
            },
        )

        lesson = Lesson.objects.get(title='Course Spoof Attempt')
        self.assertEqual(lesson.course, self.course)

    def test_tenant_admin_cannot_create_lesson_on_other_tenant_course(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-create', args=[self.other_course.id]),
            {'title': 'Cross Tenant Lesson', 'content': 'Nope', 'order': 2},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Lesson.objects.filter(title='Cross Tenant Lesson').exists())

    def test_expired_tenant_admin_cannot_create_lesson(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-create', args=[self.course.id]),
            {'title': 'Expired Lesson', 'content': 'Nope', 'order': 2},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Lesson.objects.filter(title='Expired Lesson').exists())
