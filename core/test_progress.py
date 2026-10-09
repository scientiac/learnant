from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, LessonProgress, Tenant, User


class LessonProgressModelTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.admin = User.objects.create_user(
            username='tenant-admin', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant,
            must_change_password=False,
        )
        self.course = Course.objects.create(tenant=self.tenant, title='Course A', creator=self.admin)
        self.other_course = Course.objects.create(tenant=self.tenant, title='Course B', creator=self.admin)
        self.lesson = Lesson.objects.create(course=self.course, title='Lesson A', content='Content', order=1)
        self.other_lesson = Lesson.objects.create(
            course=self.other_course, title='Lesson B', content='Content', order=1
        )
        self.assignment = CourseAssignment.objects.create(
            tenant=self.tenant, course=self.course, learner=self.learner
        )

    def test_progress_lesson_must_belong_to_assigned_course(self):
        progress = LessonProgress(assignment=self.assignment, lesson=self.other_lesson, is_complete=True)

        with self.assertRaises(ValidationError):
            progress.full_clean()


class LessonProgressViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.other_tenant = Tenant.objects.create(name='Tenant B')
        self.admin = User.objects.create_user(
            username='tenant-admin', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.other_admin = User.objects.create_user(
            username='other-admin', password='test', role=User.Role.TENANT_ADMIN, tenant=self.other_tenant
        )
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant,
            must_change_password=False,
        )
        self.other_learner = User.objects.create_user(
            username='other-learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant,
            must_change_password=False,
        )
        self.course = Course.objects.create(tenant=self.tenant, title='Course A', creator=self.admin)
        self.other_course = Course.objects.create(
            tenant=self.other_tenant, title='Course B', creator=self.other_admin
        )
        self.lesson = Lesson.objects.create(course=self.course, title='Lesson A', content='Content', order=1)
        self.assignment = CourseAssignment.objects.create(
            tenant=self.tenant, course=self.course, learner=self.learner
        )

    def test_assigned_learner_can_mark_own_lesson_complete(self):
        self.client.login(username='learner', password='test')

        response = self.client.post(reverse('lesson-mark-complete', args=[self.course.id, self.lesson.id]))

        self.assertEqual(response.status_code, 302)
        progress = LessonProgress.objects.get(assignment=self.assignment, lesson=self.lesson)
        self.assertTrue(progress.is_complete)
        self.assertIsNotNone(progress.completed_at)

    def test_unassigned_learner_cannot_mark_lesson_complete_by_id(self):
        self.client.login(username='other-learner', password='test')

        response = self.client.post(reverse('lesson-mark-complete', args=[self.course.id, self.lesson.id]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(LessonProgress.objects.exists())

    def test_learner_cannot_mark_other_course_lesson_complete(self):
        other_lesson = Lesson.objects.create(
            course=self.other_course, title='Other Lesson', content='Other', order=1
        )
        self.client.login(username='learner', password='test')

        response = self.client.post(
            reverse('lesson-mark-complete', args=[self.other_course.id, other_lesson.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(LessonProgress.objects.exists())

    def test_expired_tenant_can_read_progress_but_not_update(self):
        LessonProgress.objects.create(assignment=self.assignment, lesson=self.lesson, is_complete=True)
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='learner', password='test')

        read_response = self.client.get(reverse('lesson-list', args=[self.course.id]))
        write_response = self.client.post(reverse('lesson-mark-complete', args=[self.course.id, self.lesson.id]))

        self.assertEqual(read_response.status_code, 200)
        self.assertContains(read_response, 'Complete')
        self.assertEqual(write_response.status_code, 403)

    def test_tenant_admin_can_view_own_tenant_progress(self):
        LessonProgress.objects.create(assignment=self.assignment, lesson=self.lesson, is_complete=True)
        self.client.login(username='tenant-admin', password='test')

        response = self.client.get(reverse('progress-list', args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'learner')
        self.assertContains(response, 'Lesson A')

    def test_tenant_admin_cannot_view_other_tenant_progress_by_id(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.get(reverse('progress-list', args=[self.other_course.id]))

        self.assertEqual(response.status_code, 404)

    def test_non_learner_cannot_mark_progress(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('lesson-mark-complete', args=[self.course.id, self.lesson.id]))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonProgress.objects.exists())
