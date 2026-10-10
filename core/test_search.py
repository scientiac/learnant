from django.test import TestCase
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, Tenant, User


class TenantAwareSearchTests(TestCase):
    def setUp(self):
        self.alpha = Tenant.objects.create(name='Alpha Learning')
        self.beta = Tenant.objects.create(name='Beta Academy')
        self.alpha_admin = User.objects.create_user(
            username='alpha-owner',
            email='owner@alpha.example',
            first_name='Avery',
            last_name='Alpha',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.alpha,
        )
        self.beta_admin = User.objects.create_user(
            username='beta-owner',
            email='owner@beta.example',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.beta,
        )
        self.alpha_learner = User.objects.create_user(
            username='alpha-learner',
            email='learner@alpha.example',
            password='test',
            role=User.Role.TENANT_USER,
            tenant=self.alpha,
            must_change_password=False,
        )
        self.beta_learner = User.objects.create_user(
            username='beta-learner',
            email='learner@beta.example',
            password='test',
            role=User.Role.TENANT_USER,
            tenant=self.beta,
            must_change_password=False,
        )
        self.alpha_course = Course.objects.create(
            tenant=self.alpha, title='Algebra Foundations', description='Linear equations', creator=self.alpha_admin
        )
        self.beta_course = Course.objects.create(
            tenant=self.beta, title='Biology Basics', description='Cell structure', creator=self.beta_admin
        )
        self.lesson = Lesson.objects.create(
            course=self.alpha_course, title='Solving Equations', description='A first lesson', content='Solve for x'
        )
        self.assignment = CourseAssignment.objects.create(
            tenant=self.alpha, course=self.alpha_course, learner=self.alpha_learner
        )

    def test_platform_search_finds_tenant_admin_owners_by_email(self):
        viewer = User.objects.create_user(username='reader', password='test', role=User.Role.SUPER_VIEWER)
        self.client.force_login(viewer)

        response = self.client.get(reverse('tenant-list'), {'q': 'owner@alpha.example'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha Learning')
        self.assertContains(response, 'alpha-owner')
        self.assertContains(response, 'owner@alpha.example')
        self.assertNotContains(response, 'Beta Academy')

    def test_platform_viewer_can_open_read_only_member_directory_and_find_owners(self):
        viewer = User.objects.create_user(username='reader', password='test', role=User.Role.SUPER_VIEWER)
        self.client.force_login(viewer)

        response = self.client.get(
            reverse('platform-tenant-users', args=[self.alpha.id]),
            {'q': 'alpha-owner'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organization admins')
        self.assertContains(response, 'alpha-owner')
        self.assertNotContains(response, 'beta-owner')
        self.assertFalse(response.context['can_edit_users'])

    def test_global_member_directory_searches_tenant_admins_and_learners_across_colonies(self):
        viewer = User.objects.create_user(username='reader', password='test', role=User.Role.SUPER_VIEWER)
        self.client.force_login(viewer)

        owners = self.client.get(reverse('platform-member-list'), {'q': 'owner@alpha.example'})
        learners = self.client.get(reverse('platform-member-list'), {'q': 'learner@beta.example'})

        self.assertContains(owners, 'alpha-owner')
        self.assertContains(owners, 'Alpha Learning')
        self.assertNotContains(owners, 'beta-owner')
        self.assertContains(learners, 'beta-learner')
        self.assertContains(learners, 'Beta Academy')
        self.assertNotContains(learners, 'alpha-learner')

    def test_tenant_user_cannot_open_cross_colony_member_directory(self):
        self.client.force_login(self.alpha_learner)

        response = self.client.get(reverse('platform-member-list'))

        self.assertEqual(response.status_code, 403)

    def test_course_and_lesson_search_are_scoped_to_visible_course_set(self):
        self.client.force_login(self.alpha_admin)

        courses = self.client.get(reverse('course-list'), {'q': 'Algebra'})
        lessons = self.client.get(reverse('lesson-list', args=[self.alpha_course.id]), {'q': 'Equations'})

        self.assertContains(courses, 'Algebra Foundations')
        self.assertNotContains(courses, 'Biology Basics')
        self.assertContains(lessons, 'Solving Equations')
        self.assertNotContains(lessons, 'Solve for x')

    def test_roster_assignment_and_progress_search_filter_only_current_colony(self):
        self.client.force_login(self.alpha_admin)

        members = self.client.get(reverse('tenant-user-list'), {'q': 'alpha-learner'})
        assignments = self.client.get(
            reverse('assignment-list', args=[self.alpha_course.id]), {'q': 'learner@alpha.example'}
        )
        progress = self.client.get(reverse('progress-list', args=[self.alpha_course.id]), {'q': 'alpha-learner'})

        self.assertContains(members, 'alpha-learner')
        self.assertNotContains(members, 'beta-learner')
        self.assertContains(assignments, 'alpha-learner')
        self.assertNotContains(assignments, 'beta-learner')
        self.assertContains(progress, 'alpha-learner')
        self.assertNotContains(progress, 'beta-learner')

    def test_assignment_picker_search_only_offers_matching_same_tenant_learners(self):
        self.client.force_login(self.alpha_admin)

        response = self.client.get(
            reverse('assignment-create', args=[self.alpha_course.id]), {'q': 'alpha-learner'}
        )

        self.assertContains(response, 'alpha-learner')
        self.assertNotContains(response, 'beta-learner')
