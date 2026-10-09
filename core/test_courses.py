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


class CourseCreateViewTests(TestCase):
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
        self.viewer = User.objects.create_user(
            username='viewer',
            password='test',
            role=User.Role.SUPER_VIEWER,
        )

    def test_course_create_requires_login(self):
        response = self.client.get(reverse('course-create'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_active_tenant_admin_can_create_course(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('course-create'),
            {'title': 'New Course', 'description': 'Created in Tenant A'},
        )

        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(title='New Course')
        self.assertEqual(course.tenant, self.tenant)
        self.assertEqual(course.creator, self.tenant_admin)

    def test_posted_tenant_id_is_ignored(self):
        self.client.login(username='tenant-admin', password='test')

        self.client.post(
            reverse('course-create'),
            {
                'title': 'Tenant Spoof Attempt',
                'description': 'Should stay in authenticated tenant',
                'tenant': self.other_tenant.id,
                'creator': self.viewer.id,
            },
        )

        course = Course.objects.get(title='Tenant Spoof Attempt')
        self.assertEqual(course.tenant, self.tenant)
        self.assertEqual(course.creator, self.tenant_admin)

    def test_learner_cannot_create_course(self):
        self.client.login(username='learner', password='test')

        response = self.client.post(reverse('course-create'), {'title': 'Nope'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Course.objects.filter(title='Nope').exists())

    def test_super_viewer_cannot_create_course(self):
        self.client.login(username='viewer', password='test')

        response = self.client.post(reverse('course-create'), {'title': 'Read Only'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Course.objects.filter(title='Read Only').exists())

    def test_expired_tenant_admin_cannot_create_course(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('course-create'), {'title': 'Expired Course'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Course.objects.filter(title='Expired Course').exists())


class CourseMutationViewTests(TestCase):
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
        self.viewer = User.objects.create_user(username='viewer', password='test', role=User.Role.SUPER_VIEWER)
        self.course = Course.objects.create(tenant=self.tenant, title='Course A', creator=self.tenant_admin)
        self.other_course = Course.objects.create(
            tenant=self.other_tenant, title='Course B', creator=self.other_admin
        )

    def test_tenant_admin_can_update_own_course(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('course-update', args=[self.course.id]),
            {'title': 'Updated Course', 'description': 'Updated'},
        )
        self.course.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.course.title, 'Updated Course')
        self.assertEqual(self.course.tenant, self.tenant)

    def test_tenant_admin_cannot_update_other_tenant_course(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('course-update', args=[self.other_course.id]),
            {'title': 'Cross Tenant Update', 'description': ''},
        )
        self.other_course.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.other_course.title, 'Course B')

    def test_expired_tenant_admin_cannot_update_course(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(
            reverse('course-update', args=[self.course.id]),
            {'title': 'Expired Update', 'description': ''},
        )

        self.assertEqual(response.status_code, 403)

    def test_learner_and_super_viewer_cannot_delete_course(self):
        self.client.login(username='learner', password='test')
        learner_response = self.client.post(reverse('course-delete', args=[self.course.id]))
        self.client.logout()
        self.client.login(username='viewer', password='test')
        viewer_response = self.client.post(reverse('course-delete', args=[self.course.id]))

        self.assertEqual(learner_response.status_code, 404)
        self.assertEqual(viewer_response.status_code, 403)
        self.assertTrue(Course.objects.filter(id=self.course.id).exists())

    def test_tenant_admin_can_delete_own_course(self):
        self.client.login(username='tenant-admin', password='test')

        response = self.client.post(reverse('course-delete', args=[self.course.id]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Course.objects.filter(id=self.course.id).exists())
