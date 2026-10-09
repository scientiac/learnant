from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Course, CourseAssignment, Tenant, User


class CsvEnrollmentTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Institute A')
        self.other_tenant = Tenant.objects.create(name='Institute B')
        self.tenant_admin = User.objects.create_user(
            username='manager-a', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.other_admin = User.objects.create_user(
            username='manager-b', password='test', role=User.Role.TENANT_ADMIN, tenant=self.other_tenant
        )
        self.platform_admin = User.objects.create_user(
            username='platform-admin', password='test', role=User.Role.ADMIN
        )
        self.viewer = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )
        self.course = Course.objects.create(
            tenant=self.tenant, title='Course A', creator=self.tenant_admin
        )
        self.other_course = Course.objects.create(
            tenant=self.other_tenant, title='Course B', creator=self.other_admin
        )

    def upload(self, content, name='students.csv'):
        return SimpleUploadedFile(name, content.encode('utf-8'), content_type='text/csv')

    def test_tenant_admin_can_download_csv_template(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.get(reverse('student-csv-template'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn(b'# Course IDs for this organization', response.content)
        self.assertIn(f'# {self.course.id}: Course A'.encode(), response.content)
        self.assertIn(b'username,email,first_name,last_name,course_ids', response.content)

    def test_manual_enrollment_form_has_profile_and_multi_course_fields(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.get(reverse('bulk-student-add'))

        self.assertContains(response, 'Add learners')
        self.assertContains(response, 'First name')
        self.assertContains(response, 'Last name')
        self.assertContains(response, 'type="checkbox"')
        self.assertContains(response, f'#{self.course.id} — Course A')
        self.assertContains(response, 'Add another learner')
        self.assertContains(response, 'Remove learner')
        self.assertContains(response, 'learners-TOTAL_FORMS" value="1"')

    def test_manual_rows_create_learners_and_assign_multiple_selected_courses(self):
        second_course = Course.objects.create(
            tenant=self.tenant, title='Course C', creator=self.tenant_admin
        )
        self.client.login(username='manager-a', password='test')
        data = {
            'action': 'manual_rows',
            'learners-TOTAL_FORMS': '3',
            'learners-INITIAL_FORMS': '0',
            'learners-MIN_NUM_FORMS': '0',
            'learners-MAX_NUM_FORMS': '100',
            'learners-0-username': 'manual_student',
            'learners-0-email': 'manual@example.test',
            'learners-0-first_name': 'Manual',
            'learners-0-last_name': 'Student',
            'learners-0-courses': [str(self.course.id), str(second_course.id)],
            'learners-1-username': '',
            'learners-1-email': 'email_only@example.test',
            'learners-1-first_name': 'Email',
            'learners-1-last_name': 'Only',
            'learners-2-username': '',
            'learners-2-email': '',
            'learners-2-first_name': '',
            'learners-2-last_name': '',
        }

        response = self.client.post(reverse('bulk-student-add'), data)

        result = response.context['manual_result']
        self.assertEqual(len(result['created_students']), 2, result)
        first = User.objects.get(username='manual_student')
        email_only = User.objects.get(email='email_only@example.test')
        self.assertEqual(first.tenant, self.tenant)
        self.assertTrue(first.must_change_password)
        self.assertEqual(
            set(first.course_assignments.values_list('course_id', flat=True)),
            {self.course.id, second_course.id},
        )
        self.assertFalse(CourseAssignment.objects.filter(learner=email_only).exists())

    def test_manual_form_rejects_foreign_course_ids_without_rejecting_other_rows(self):
        self.client.login(username='manager-a', password='test')
        data = {
            'action': 'manual_rows',
            'learners-TOTAL_FORMS': '2',
            'learners-INITIAL_FORMS': '0',
            'learners-MIN_NUM_FORMS': '0',
            'learners-MAX_NUM_FORMS': '100',
            'learners-0-username': 'foreign_course_student',
            'learners-0-email': '',
            'learners-0-first_name': '',
            'learners-0-last_name': '',
            'learners-0-courses': str(self.other_course.id),
            'learners-1-username': 'valid_student',
            'learners-1-email': '',
            'learners-1-first_name': '',
            'learners-1-last_name': '',
            'learners-1-courses': str(self.course.id),
        }

        response = self.client.post(reverse('bulk-student-add'), data)

        self.assertEqual(len(response.context['manual_result']['created_students']), 1)
        self.assertEqual(response.context['manual_result']['skipped_count'], 1)
        valid = User.objects.get(username='valid_student')
        self.assertEqual(valid.tenant, self.tenant)
        self.assertFalse(User.objects.filter(username='foreign_course_student').exists())

    def test_csv_import_creates_rows_independently_and_assigns_only_local_courses(self):
        self.client.login(username='manager-a', password='test')
        csv_content = (
            '# Course IDs for this organization (separate multiple IDs with semicolons):\n'
            f'# {self.course.id}: Course A\n'
            f'# {self.other_course.id}: Course B\n\n'
            'username,email,first_name,last_name,course_ids\n'
            f'alice,alice@example.test,Alice,A,{self.course.id}\n'
            ',bob@example.test,Bob,B,\n'
            'alice,duplicate@example.test,Duplicate,Row,\n'
            'bad_user!,bad-email,Invalid,Row,\n'
            f'charlie,charlie@example.test,Charlie,C,{self.other_course.id}\n'
        )

        response = self.client.post(
            reverse('bulk-student-add'),
            {'action': 'import_csv', 'csv_file': self.upload(csv_content)},
        )

        self.assertEqual(response.status_code, 200)
        result = response.context['csv_result']
        self.assertEqual(len(result['created_students']), 2, result)
        self.assertEqual(result['skipped_count'], 3)
        alice = User.objects.get(username='alice')
        bob = User.objects.get(email='bob@example.test')
        self.assertEqual(alice.tenant, self.tenant)
        self.assertEqual(alice.role, User.Role.TENANT_USER)
        self.assertTrue(alice.must_change_password)
        self.assertEqual(bob.tenant, self.tenant)
        self.assertTrue(bob.must_change_password)
        self.assertTrue(CourseAssignment.objects.filter(tenant=self.tenant, course=self.course, learner=alice).exists())
        self.assertFalse(CourseAssignment.objects.filter(course=self.other_course).exists())
        self.assertEqual(len(result['row_errors']), 3)

    def test_csv_import_allows_no_immediate_course_assignment(self):
        self.client.login(username='manager-a', password='test')
        content = 'username,email,first_name,last_name,course_ids\nsolo,solo@example.test,Solo,Learner,\n'

        response = self.client.post(
            reverse('bulk-student-add'),
            {'action': 'import_csv', 'csv_file': self.upload(content)},
        )

        self.assertEqual(len(response.context['csv_result']['created_students']), 1)
        learner = User.objects.get(username='solo')
        self.assertFalse(CourseAssignment.objects.filter(learner=learner).exists())

    def test_duplicate_existing_accounts_are_skipped_without_aborting_valid_rows(self):
        User.objects.create_user(
            username='already', password='test', role=User.Role.TENANT_USER,
            tenant=self.tenant, must_change_password=False,
        )
        self.client.login(username='manager-a', password='test')
        content = 'username,email,first_name,last_name,course_ids\nalready,,Existing,User,\nnew,new@example.test,New,User,\n'

        response = self.client.post(
            reverse('bulk-student-add'),
            {'action': 'import_csv', 'csv_file': self.upload(content)},
        )

        self.assertEqual(len(response.context['csv_result']['created_students']), 1)
        self.assertEqual(response.context['csv_result']['skipped_count'], 1)
        self.assertTrue(User.objects.filter(username='new', tenant=self.tenant).exists())

    def test_bad_header_fails_without_creating_any_users(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.post(
            reverse('bulk-student-add'),
            {'action': 'import_csv', 'csv_file': self.upload('wrong,header\na,b\n')},
        )

        self.assertIn('Missing columns', response.context['csv_result']['file_error'])
        self.assertEqual(response.context['csv_result']['created_students'], [])
        self.assertEqual(User.objects.filter(tenant=self.tenant, role=User.Role.TENANT_USER).count(), 0)

    def test_platform_admin_import_binds_learners_to_selected_tenant(self):
        self.client.login(username='platform-admin', password='test')
        content = 'username,email,first_name,last_name\nmanaged,managed@example.test,Managed,User\n'

        response = self.client.post(
            reverse('tenant-bulk-student-add', args=[self.other_tenant.id]),
            {'action': 'import_csv', 'csv_file': self.upload(content)},
        )

        self.assertEqual(len(response.context['csv_result']['created_students']), 1)
        learner = User.objects.get(username='managed')
        self.assertEqual(learner.tenant, self.other_tenant)
        self.assertTrue(learner.must_change_password)

    def test_super_viewer_cannot_import_or_download_tenant_template(self):
        self.client.login(username='viewer', password='test')

        import_response = self.client.post(
            reverse('tenant-bulk-student-add', args=[self.tenant.id]),
            {'action': 'import_csv', 'csv_file': self.upload('username,email,first_name,last_name\n')},
        )
        template_response = self.client.get(
            reverse('tenant-student-csv-template', args=[self.tenant.id])
        )

        self.assertEqual(import_response.status_code, 403)
        self.assertEqual(template_response.status_code, 403)

    def test_expired_tenant_cannot_import_csv(self):
        self.tenant.status = Tenant.Status.EXPIRED
        self.tenant.save()
        self.client.login(username='manager-a', password='test')
        content = 'username,email,first_name,last_name\nexpired,expired@example.test,Expired,User\n'

        response = self.client.post(
            reverse('bulk-student-add'),
            {'action': 'import_csv', 'csv_file': self.upload(content)},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='expired').exists())
