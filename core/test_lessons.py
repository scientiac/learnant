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

    def test_lesson_create_form_suggests_next_order(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.get(reverse('lesson-create', args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form']['order'].value(), 2)

    def test_blank_lesson_order_is_assigned_next_sequence(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-create', args=[self.course.id]),
            {'title': 'Auto Ordered Lesson', 'content': 'Content', 'order': ''},
        )

        self.assertEqual(response.status_code, 302)
        lesson = Lesson.objects.get(title='Auto Ordered Lesson')
        self.assertEqual(lesson.order, 2)

    def test_model_auto_appends_when_default_order_would_collide(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title='Model Auto Ordered Lesson',
            content='Content',
        )

        self.assertEqual(lesson.order, 2)

    def test_duplicate_new_lesson_order_is_safely_appended(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title='Duplicate Order Lesson',
            content='Content',
            order=1,
        )

        self.assertEqual(lesson.order, 2)

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

    def test_tenant_admin_can_update_own_lesson(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-update', args=[self.course.id, self.lesson.id]),
            {'title': 'Updated Lesson', 'content': 'Updated content', 'order': 1},
        )
        self.lesson.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.lesson.title, 'Updated Lesson')
        self.assertEqual(self.lesson.course, self.course)

    def test_tenant_admin_cannot_update_other_tenant_lesson(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-update', args=[self.other_course.id, self.other_lesson.id]),
            {'title': 'Cross Tenant Update', 'content': 'Nope', 'order': 1},
        )
        self.other_lesson.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.other_lesson.title, 'Tenant B Lesson')

    def test_expired_tenant_admin_cannot_delete_lesson(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('lesson-delete', args=[self.course.id, self.lesson.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_super_viewer_cannot_delete_lesson(self):
        self.client.login(username='viewer', password='test')

        response = self.client.post(reverse('lesson-delete', args=[self.course.id, self.lesson.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_tenant_admin_can_delete_own_lesson(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('lesson-delete', args=[self.course.id, self.lesson.id]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_tenant_admin_can_reorder_lessons_without_order_collisions(self):
        second = Lesson.objects.create(
            course=self.course, title='Second Lesson', content='Second', order=2
        )
        third = Lesson.objects.create(
            course=self.course, title='Third Lesson', content='Third', order=3
        )
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-reorder', args=[self.course.id]),
            {'lesson_id': third.id, 'direction': 'up'},
        )

        self.assertEqual(response.status_code, 302)
        ordered = list(Lesson.objects.filter(course=self.course).order_by('order'))
        self.assertEqual([lesson.title for lesson in ordered], [
            'Tenant A Lesson', 'Third Lesson', 'Second Lesson'
        ])
        self.assertEqual([lesson.order for lesson in ordered], [1, 2, 3])

    def test_tenant_admin_cannot_reorder_foreign_course(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-reorder', args=[self.other_course.id]),
            {'lesson_id': self.other_lesson.id, 'direction': 'up'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.other_lesson.order, 1)

    def test_expired_tenant_cannot_reorder_lessons(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-reorder', args=[self.course.id]),
            {'lesson_id': self.lesson.id, 'direction': 'down'},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.lesson.order, 1)

    def test_reorder_rejects_invalid_direction(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('lesson-reorder', args=[self.course.id]),
            {'lesson_id': self.lesson.id, 'direction': 'sideways'},
        )

        self.assertEqual(response.status_code, 403)
