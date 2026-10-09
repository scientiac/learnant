from django.test import TestCase
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, Tenant, User
from .permissions import can_manage_tenant_learning


class PlatformRoleTenantManagementTests(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Institute A')
        self.tenant_b = Tenant.objects.create(name='Institute B')
        self.super_admin = User.objects.create_user(
            username='root', password='test', role=User.Role.SUPER_ADMIN
        )
        self.admin = User.objects.create_user(username='ops', password='test', role=User.Role.ADMIN)
        self.viewer = User.objects.create_user(
            username='auditor', password='test', role=User.Role.SUPER_VIEWER
        )
        self.tenant_admin = User.objects.create_user(
            username='manager-a', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant_a
        )
        self.tenant_admin_b = User.objects.create_user(
            username='manager-b', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant_b
        )
        self.learner = User.objects.create_user(
            username='learner-a', password='test', role=User.Role.TENANT_USER, tenant=self.tenant_a
        )
        self.other_learner = User.objects.create_user(
            username='learner-b', password='test', role=User.Role.TENANT_USER, tenant=self.tenant_b
        )
        self.second_other_learner = User.objects.create_user(
            username='learner-b2', password='test', role=User.Role.TENANT_USER, tenant=self.tenant_b
        )
        self.course_a = Course.objects.create(
            tenant=self.tenant_a, title='Course A', creator=self.tenant_admin
        )
        self.course_b = Course.objects.create(
            tenant=self.tenant_b, title='Course B', creator=self.tenant_admin_b
        )
        self.lesson_b = Lesson.objects.create(
            course=self.course_b, title='Lesson B', content='Content', order=1
        )

    def test_platform_admins_can_manage_all_active_tenant_content(self):
        for platform_admin in (self.super_admin, self.admin):
            with self.subTest(role=platform_admin.role):
                self.assertTrue(can_manage_tenant_learning(platform_admin, self.tenant_a))
                self.assertTrue(can_manage_tenant_learning(platform_admin, self.tenant_b))

    def test_super_viewer_is_read_only_and_tenant_admin_is_scoped(self):
        self.assertFalse(can_manage_tenant_learning(self.viewer, self.tenant_a))
        self.assertTrue(can_manage_tenant_learning(self.tenant_admin, self.tenant_a))
        self.assertFalse(can_manage_tenant_learning(self.tenant_admin, self.tenant_b))
        self.assertFalse(can_manage_tenant_learning(self.learner, self.tenant_a))

    def test_platform_admin_course_list_exposes_manage_actions(self):
        self.client.login(username='ops', password='test')

        response = self.client.get(reverse('course-list'))

        self.assertContains(response, 'Course A')
        self.assertContains(response, 'Course B')
        self.assertContains(response, reverse('course-update', args=[self.course_b.id]))
        self.assertContains(response, reverse('assignment-list', args=[self.course_b.id]))
        self.assertContains(response, reverse('progress-list', args=[self.course_b.id]))
        self.assertContains(response, reverse('course-create'))

    def test_super_viewer_sees_content_without_manage_actions(self):
        self.client.login(username='auditor', password='test')

        response = self.client.get(reverse('course-list'))
        tenant_response = self.client.get(reverse('tenant-course-list', args=[self.tenant_b.id]))

        self.assertContains(response, 'Course B')
        self.assertNotContains(response, reverse('course-update', args=[self.course_b.id]))
        self.assertNotContains(response, reverse('assignment-list', args=[self.course_b.id]))
        self.assertEqual(tenant_response.status_code, 200)
        self.assertContains(tenant_response, 'Course B')
        self.assertNotContains(tenant_response, reverse('course-update', args=[self.course_b.id]))

    def test_platform_admin_can_create_course_for_selected_tenant(self):
        self.client.login(username='ops', password='test')

        response = self.client.post(
            reverse('course-create'),
            {'title': 'Platform Course', 'description': 'Created by operations', 'tenant': self.tenant_b.id},
        )

        self.assertEqual(response.status_code, 302)
        created = Course.objects.get(title='Platform Course')
        self.assertEqual(created.tenant, self.tenant_b)
        self.assertEqual(created.creator, self.admin)

    def test_tenant_admin_cannot_change_course_tenant_by_posting_foreign_tenant(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.post(
            reverse('course-create'),
            {'title': 'Tenant-bound Course', 'description': '', 'tenant': self.tenant_b.id},
        )

        self.assertEqual(response.status_code, 302)
        created = Course.objects.get(title='Tenant-bound Course')
        self.assertEqual(created.tenant, self.tenant_a)

    def test_platform_admin_can_update_lesson_assignment_and_view_progress(self):
        assignment = CourseAssignment.objects.create(
            tenant=self.tenant_b, course=self.course_b, learner=self.other_learner
        )
        self.client.login(username='ops', password='test')

        update_response = self.client.post(
            reverse('lesson-update', args=[self.course_b.id, self.lesson_b.id]),
            {'title': 'Updated by platform', 'content': 'Updated', 'order': 1},
        )
        new_assignment_response = self.client.post(
            reverse('assignment-create', args=[self.course_b.id]),
            {'learner': self.second_other_learner.id},
        )
        progress_response = self.client.get(reverse('progress-list', args=[self.course_b.id]))
        revoke_response = self.client.post(
            reverse('assignment-delete', args=[self.course_b.id, assignment.id])
        )

        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(new_assignment_response.status_code, 302)
        self.assertEqual(progress_response.status_code, 200)
        self.assertEqual(revoke_response.status_code, 302)
        self.lesson_b.refresh_from_db()
        self.assertEqual(self.lesson_b.title, 'Updated by platform')
        created_assignment = CourseAssignment.objects.get(
            course=self.course_b, learner=self.second_other_learner
        )
        self.assertEqual(created_assignment.tenant, self.tenant_b)
        self.assertFalse(CourseAssignment.objects.filter(id=assignment.id).exists())

    def test_platform_admin_cannot_mutate_expired_tenant(self):
        self.tenant_b.status = Tenant.Status.EXPIRED
        self.tenant_b.save()
        self.client.login(username='root', password='test')

        course_response = self.client.post(
            reverse('course-update', args=[self.course_b.id]), {'title': 'Forbidden', 'description': ''}
        )
        lesson_response = self.client.post(
            reverse('lesson-delete', args=[self.course_b.id, self.lesson_b.id])
        )

        self.assertEqual(course_response.status_code, 403)
        self.assertEqual(lesson_response.status_code, 403)
        self.course_b.refresh_from_db()
        self.assertEqual(self.course_b.title, 'Course B')
        self.assertTrue(Lesson.objects.filter(id=self.lesson_b.id).exists())

    def test_tenant_directory_exposes_platform_management_links_not_to_viewer(self):
        self.client.login(username='ops', password='test')
        admin_response = self.client.get(reverse('tenant-list'))
        self.client.logout()
        self.client.login(username='auditor', password='test')
        viewer_response = self.client.get(reverse('tenant-list'))

        self.assertContains(admin_response, reverse('tenant-course-list', args=[self.tenant_a.id]))
        self.assertContains(admin_response, reverse('tenant-organization-settings', args=[self.tenant_a.id]))
        self.assertContains(admin_response, reverse('tenant-bulk-student-add', args=[self.tenant_a.id]))
        self.assertNotContains(viewer_response, reverse('tenant-organization-settings', args=[self.tenant_a.id]))
        self.assertNotContains(viewer_response, reverse('tenant-bulk-student-add', args=[self.tenant_a.id]))

    def test_platform_admin_can_manage_selected_tenant_settings_and_learners(self):
        self.client.login(username='ops', password='test')

        organization_response = self.client.post(
            reverse('tenant-organization-settings', args=[self.tenant_b.id]),
            {'name': 'Institute B Updated', 'brand_color': '#112233'},
        )
        bulk_response = self.client.post(
            reverse('tenant-bulk-student-add', args=[self.tenant_b.id]),
            {'students': 'platform_enrolled_student'},
        )

        self.assertEqual(organization_response.status_code, 302)
        self.assertEqual(bulk_response.status_code, 200)
        self.tenant_b.refresh_from_db()
        enrolled = User.objects.get(username='platform_enrolled_student')
        self.assertEqual(self.tenant_b.name, 'Institute B Updated')
        self.assertEqual(enrolled.role, User.Role.TENANT_USER)
        self.assertEqual(enrolled.tenant, self.tenant_b)

    def test_super_viewer_cannot_mutate_selected_tenant_settings_or_learners(self):
        self.client.login(username='auditor', password='test')

        settings_response = self.client.post(
            reverse('tenant-organization-settings', args=[self.tenant_b.id]),
            {'name': 'Viewer Change', 'brand_color': '#112233'},
        )
        bulk_response = self.client.post(
            reverse('tenant-bulk-student-add', args=[self.tenant_b.id]),
            {'students': 'viewer_created_student'},
        )

        self.assertEqual(settings_response.status_code, 403)
        self.assertEqual(bulk_response.status_code, 403)
        self.assertFalse(User.objects.filter(username='viewer_created_student').exists())
