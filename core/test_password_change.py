from django.test import TestCase
from django.urls import reverse

from .models import Tenant, User


class RequiredPasswordChangeTests(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name='Institute A')
        self.user = User.objects.create_user(
            username='new-learner',
            password='Temporary!Password123',
            role=User.Role.TENANT_USER,
            tenant=tenant,
            must_change_password=True,
        )

    def test_new_learners_default_to_password_change_but_admins_do_not(self):
        learner = User.objects.create_user(
            username='new-default-learner', password='test', role=User.Role.TENANT_USER,
            tenant=self.user.tenant,
        )
        tenant_admin = User.objects.create_user(
            username='new-admin', password='test', role=User.Role.TENANT_ADMIN,
            tenant=self.user.tenant,
        )

        self.assertTrue(learner.must_change_password)
        self.assertFalse(tenant_admin.must_change_password)

    def test_must_change_user_is_redirected_before_course_access(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('course-list'))

        self.assertRedirects(response, reverse('password-change'))

    def test_password_change_screen_and_logout_are_exempt(self):
        self.client.force_login(self.user)

        change_response = self.client.get(reverse('password-change'))
        logout_response = self.client.post(reverse('logout'))

        self.assertEqual(change_response.status_code, 200)
        self.assertContains(change_response, 'Change your temporary password')
        self.assertEqual(logout_response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_successful_password_change_clears_flag_and_unlocks_app(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('password-change'),
            {
                'old_password': 'Temporary!Password123',
                'new_password1': 'NewSecure!Password889',
                'new_password2': 'NewSecure!Password889',
            },
        )
        self.user.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(self.user.check_password('NewSecure!Password889'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_wrong_old_password_keeps_access_blocked(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('password-change'),
            {
                'old_password': 'wrong password',
                'new_password1': 'NewSecure!Password889',
                'new_password2': 'NewSecure!Password889',
            },
        )
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user.must_change_password)
        self.assertEqual(self.client.get(reverse('course-list')).url, reverse('password-change'))
