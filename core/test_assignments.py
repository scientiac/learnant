from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, Tenant, User


class CourseAssignmentModelTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Tenant A')
        self.other_tenant = Tenant.objects.create(name='Tenant B')
        self.tenant_admin = User.objects.create_user(
            username='tenant-admin', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.learner = User.objects.create_user(
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant
        )
        self.other_learner = User.objects.create_user(
            username='other-learner', password='test', role=User.Role.TENANT_USER, tenant=self.other_tenant
        )
        self.course = Course.objects.create(tenant=self.tenant, title='Course A', creator=self.tenant_admin)

    def test_assignment_requires_same_tenant_learner(self):
        assignment = CourseAssignment(tenant=self.tenant, course=self.course, learner=self.other_learner)

        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_assignment_requires_tenant_user(self):
        assignment = CourseAssignment(tenant=self.tenant, course=self.course, learner=self.tenant_admin)

        with self.assertRaises(ValidationError):
            assignment.full_clean()


class CourseAssignmentViewTests(TestCase):
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
            username='learner', password='test', role=User.Role.TENANT_USER, tenant=self.tenant
        )
        self.other_learner = User.objects.create_user(
            username='other-learner', password='test', role=User.Role.TENANT_USER, tenant=self.other_tenant
        )
        self.viewer = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )
        self.course = Course.objects.create(tenant=self.tenant, title='Course A', creator=self.tenant_admin)
        self.other_course = Course.objects.create(
            tenant=self.other_tenant, title='Course B', creator=self.other_admin
        )
        self.lesson = Lesson.objects.create(course=self.course, title='Lesson A', content='Content', order=1)

    def test_assignment_list_requires_login(self):
        response = self.client.get(reverse('assignment-list', args=[self.course.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_tenant_admin_can_assign_same_tenant_learner(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('assignment-create', args=[self.course.id]), {'learner': self.learner.id}
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CourseAssignment.objects.filter(
                tenant=self.tenant, course=self.course, learner=self.learner
            ).exists()
        )

    def test_tenant_admin_cannot_assign_other_tenant_learner(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('assignment-create', args=[self.course.id]), {'learner': self.other_learner.id}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CourseAssignment.objects.filter(learner=self.other_learner).exists())

    def test_tenant_admin_cannot_assign_other_tenant_course(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('assignment-create', args=[self.other_course.id]), {'learner': self.learner.id}
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(CourseAssignment.objects.exists())

    def test_expired_tenant_admin_cannot_assign_course(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('assignment-create', args=[self.course.id]), {'learner': self.learner.id}
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CourseAssignment.objects.exists())

    def test_super_viewer_cannot_view_assignment_management(self):
        self.client.login(username='viewer', password='test')

        response = self.client.get(reverse('assignment-list', args=[self.course.id]))

        self.assertEqual(response.status_code, 403)

    def test_assigned_learner_sees_course_and_lessons(self):
        CourseAssignment.objects.create(tenant=self.tenant, course=self.course, learner=self.learner)
        self.client.login(username='learner', password='test')

        course_response = self.client.get(reverse('course-list'))
        lesson_response = self.client.get(reverse('lesson-list', args=[self.course.id]))

        self.assertContains(course_response, self.course.title)
        self.assertContains(lesson_response, self.lesson.title)
        self.assertNotContains(course_response, self.other_course.title)

    def test_unassigned_learner_cannot_access_course_lessons_by_id(self):
        self.client.login(username='learner', password='test')

        response = self.client.get(reverse('lesson-list', args=[self.course.id]))

        self.assertEqual(response.status_code, 404)

    def test_tenant_admin_can_revoke_own_assignment(self):
        assignment = CourseAssignment.objects.create(
            tenant=self.tenant, course=self.course, learner=self.learner
        )
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('assignment-delete', args=[self.course.id, assignment.id]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(CourseAssignment.objects.filter(id=assignment.id).exists())

    def test_tenant_admin_cannot_revoke_other_tenant_assignment(self):
        other_assignment = CourseAssignment.objects.create(
            tenant=self.other_tenant, course=self.other_course, learner=self.other_learner
        )
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('assignment-delete', args=[self.other_course.id, other_assignment.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(CourseAssignment.objects.filter(id=other_assignment.id).exists())

    def test_expired_tenant_admin_cannot_revoke_assignment(self):
        assignment = CourseAssignment.objects.create(
            tenant=self.tenant, course=self.course, learner=self.learner
        )
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('assignment-delete', args=[self.course.id, assignment.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(CourseAssignment.objects.filter(id=assignment.id).exists())
