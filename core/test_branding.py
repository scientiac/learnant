from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Tenant, User


PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'test-image-payload'


class BrandingUploadTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.tenant = Tenant.objects.create(name='Institute A')
        self.other_tenant = Tenant.objects.create(name='Institute B')
        self.tenant_admin = User.objects.create_user(
            username='manager-a',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.tenant,
            must_change_password=False,
        )
        self.other_admin = User.objects.create_user(
            username='manager-b',
            password='test',
            role=User.Role.TENANT_ADMIN,
            tenant=self.other_tenant,
            must_change_password=False,
        )
        self.learner = User.objects.create_user(
            username='learner-a',
            password='test',
            role=User.Role.TENANT_USER,
            tenant=self.tenant,
            must_change_password=False,
        )
        self.viewer = User.objects.create_user(
            username='viewer', password='test', role=User.Role.SUPER_VIEWER
        )

    def test_tenant_admin_can_upload_logo_and_contact_details(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.post(
            reverse('organization-settings'),
            {
                'name': 'Institute A',
                'brand_color': '#123456',
                'address': '1 Learning Road',
                'contact_phone': '+1 555 0100',
                'support_email': 'support@example.test',
                'website': 'https://example.test',
                'logo': SimpleUploadedFile('logo.png', PNG_BYTES, content_type='image/png'),
            },
        )
        self.tenant.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.tenant.address, '1 Learning Road')
        self.assertEqual(self.tenant.support_email, 'support@example.test')
        self.assertTrue(self.tenant.logo)
        logo_response = self.client.get(reverse('tenant-logo', args=[self.tenant.id]))
        self.assertEqual(logo_response.status_code, 200)
        self.assertEqual(logo_response['Content-Type'], 'image/png')

    def test_logo_endpoint_denies_cross_tenant_access(self):
        self.tenant.logo.save(
            'logo.png', SimpleUploadedFile('logo.png', PNG_BYTES, content_type='image/png')
        )
        self.tenant.save()
        self.client.login(username='manager-b', password='test')

        response = self.client.get(reverse('tenant-logo', args=[self.tenant.id]))

        self.assertEqual(response.status_code, 404)

    def test_user_can_upload_and_read_own_avatar(self):
        self.client.login(username='learner-a', password='test')

        response = self.client.post(
            reverse('profile-settings'),
            {
                'first_name': 'Learner',
                'last_name': 'One',
                'email': 'learner@example.test',
                'avatar': SimpleUploadedFile('avatar.png', PNG_BYTES, content_type='image/png'),
            },
        )
        self.learner.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(self.learner.avatar)
        avatar_response = self.client.get(reverse('user-avatar', args=[self.learner.id]))
        self.assertEqual(avatar_response.status_code, 200)
        self.assertEqual(avatar_response['Content-Type'], 'image/png')

    def test_tenant_user_cannot_read_another_users_avatar(self):
        self.tenant_admin.avatar.save(
            'manager.png', SimpleUploadedFile('manager.png', PNG_BYTES, content_type='image/png')
        )
        self.tenant_admin.save()
        self.client.login(username='learner-a', password='test')

        response = self.client.get(reverse('user-avatar', args=[self.tenant_admin.id]))

        self.assertEqual(response.status_code, 404)

    def test_tenant_admin_can_read_colony_member_avatar(self):
        self.learner.avatar.save(
            'learner.png', SimpleUploadedFile('learner.png', PNG_BYTES, content_type='image/png')
        )
        self.learner.save()
        self.client.login(username='manager-a', password='test')

        response = self.client.get(reverse('user-avatar', args=[self.learner.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_invalid_image_bytes_are_rejected(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.post(
            reverse('organization-settings'),
            {
                'name': self.tenant.name,
                'brand_color': self.tenant.brand_color,
                'address': '',
                'contact_phone': '',
                'support_email': '',
                'website': '',
                'logo': SimpleUploadedFile('fake.png', b'<script>bad</script>', content_type='image/png'),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.logo)
