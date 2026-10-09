from django.core.exceptions import ValidationError
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, LessonAsset, Tenant, User


class LessonStudyViewTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.tenant = Tenant.objects.create(name='Institute A')
        self.other_tenant = Tenant.objects.create(name='Institute B')
        self.tenant_admin = User.objects.create_user(
            username='manager-a', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.other_admin = User.objects.create_user(
            username='manager-b', password='test', role=User.Role.TENANT_ADMIN, tenant=self.other_tenant
        )
        self.learner = User.objects.create_user(
            username='learner-a', password='test', role=User.Role.TENANT_USER, tenant=self.tenant,
            must_change_password=False,
        )
        self.unassigned_learner = User.objects.create_user(
            username='learner-unassigned', password='test', role=User.Role.TENANT_USER, tenant=self.tenant,
            must_change_password=False,
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
        self.first = Lesson.objects.create(
            course=self.course,
            title='Introduction',
            content='# Welcome\n\nGFM **bold** and math $x^2$.',
            order=1,
            video_url='https://youtu.be/abcDEF123_-',
        )
        self.second = Lesson.objects.create(
            course=self.course, title='Practice', content='Try an exercise.', order=2
        )
        self.other_lesson = Lesson.objects.create(
            course=self.other_course, title='Private lesson', content='Other tenant text.', order=1
        )
        self.assignment = CourseAssignment.objects.create(
            tenant=self.tenant, course=self.course, learner=self.learner
        )

    def test_assigned_learner_study_page_has_markdown_video_syllabus_and_navigation(self):
        self.client.login(username='learner-a', password='test')

        response = self.client.get(reverse('lesson-detail', args=[self.course.id, self.first.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Course syllabus')
        self.assertContains(response, reverse('lesson-detail', args=[self.course.id, self.second.id]))
        self.assertContains(response, 'youtube-nocookie.com/embed/abcDEF123_-')
        self.assertContains(response, 'marked.parse')
        self.assertContains(response, 'DOMPurify.sanitize')
        self.assertContains(response, 'katex')
        self.assertContains(response, 'Mark complete')

    def test_lesson_study_route_hides_unassigned_and_foreign_lessons(self):
        self.client.login(username='learner-unassigned', password='test')
        unassigned_response = self.client.get(
            reverse('lesson-detail', args=[self.course.id, self.first.id])
        )
        self.client.logout()
        self.client.login(username='learner-a', password='test')
        foreign_response = self.client.get(
            reverse('lesson-detail', args=[self.other_course.id, self.other_lesson.id])
        )

        self.assertEqual(unassigned_response.status_code, 404)
        self.assertEqual(foreign_response.status_code, 404)

    def test_super_viewer_can_read_study_page_but_cannot_complete(self):
        self.client.login(username='viewer', password='test')

        response = self.client.get(reverse('lesson-detail', args=[self.other_course.id, self.other_lesson.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.other_lesson.title)
        self.assertNotContains(response, 'Mark complete')

    def test_mark_complete_redirects_back_to_study_page(self):
        self.client.login(username='learner-a', password='test')

        response = self.client.post(
            reverse('lesson-mark-complete', args=[self.course.id, self.first.id])
        )

        self.assertRedirects(response, reverse('lesson-detail', args=[self.course.id, self.first.id]))

    def test_study_page_escapes_lesson_source_before_sanitized_rendering(self):
        self.first.content = '<script>alert(1)</script>\n\n<img src=x onerror=alert(2)>'
        self.first.save()
        self.client.login(username='learner-a', password='test')

        response = self.client.get(reverse('lesson-detail', args=[self.course.id, self.first.id]))

        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_lesson_description_and_uploaded_image_are_added_to_markdown(self):
        self.client.login(username='manager-a', password='test')
        response = self.client.post(
            reverse('lesson-create', args=[self.course.id]),
            {
                'title': 'Diagram Lesson',
                'description': 'A short summary.',
                'content': 'Study this diagram.',
                'order': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        lesson = Lesson.objects.get(title='Diagram Lesson')
        image = SimpleUploadedFile(
            'diagram.png', b'\x89PNG\r\n\x1a\nimage-bytes', content_type='image/png'
        )
        upload_response = self.client.post(
            reverse('lesson-asset-upload', args=[self.course.id, lesson.id]),
            {'media_file': image, 'content': lesson.content},
        )
        self.assertEqual(upload_response.status_code, 201, upload_response.content)
        self.assertEqual(upload_response.json()['kind'], 'image')
        asset = LessonAsset.objects.get(lesson=lesson)
        lesson.refresh_from_db()
        self.assertEqual(lesson.description, 'A short summary.')
        self.assertIn(f'![diagram](/lesson-assets/{asset.public_id}/)', lesson.content)
        self.assertTrue(asset.file.storage.exists(asset.file.name))

        detail_response = self.client.get(reverse('lesson-detail', args=[self.course.id, lesson.id]))
        self.assertContains(detail_response, lesson.description)
        self.assertContains(detail_response, f'/lesson-assets/{asset.public_id}/')
        self.assertRedirects(
            response,
            reverse('lesson-update', args=[self.course.id, lesson.id]),
        )
        editor_response = self.client.get(reverse('lesson-update', args=[self.course.id, lesson.id]))
        self.assertContains(editor_response, f'![diagram](/lesson-assets/{asset.public_id}/)')
        self.client.force_login(self.learner)
        media_response = self.client.get(reverse('lesson-asset', args=[asset.public_id]))
        self.assertEqual(media_response.status_code, 200)
        self.assertEqual(media_response['Content-Type'], 'image/png')

    def test_uploaded_lesson_asset_requires_access_to_its_assigned_course(self):
        asset = LessonAsset.objects.create(
            lesson=self.first,
            kind=LessonAsset.Kind.IMAGE,
            mime_type='image/png',
            file=SimpleUploadedFile('image.png', b'image', content_type='image/png'),
        )
        self.client.force_login(self.unassigned_learner)

        response = self.client.get(reverse('lesson-asset', args=[asset.public_id]))

        self.assertEqual(response.status_code, 404)

    def test_uploaded_video_is_stored_and_embedded_in_lesson_markdown(self):
        self.client.login(username='manager-a', password='test')
        response = self.client.post(
            reverse('lesson-create', args=[self.course.id]),
            {
                'title': 'Video Lesson',
                'description': 'Watch the walkthrough.',
                'content': 'Introduction.',
                'order': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        lesson = Lesson.objects.get(title='Video Lesson')
        video = SimpleUploadedFile('walkthrough.mp4', b'video bytes', content_type='video/mp4')
        upload_response = self.client.post(
            reverse('lesson-asset-upload', args=[self.course.id, lesson.id]),
            {'media_file': video, 'content': lesson.content},
        )
        self.assertEqual(upload_response.status_code, 201, upload_response.content)
        lesson.refresh_from_db()
        asset = LessonAsset.objects.get(lesson=lesson, kind=LessonAsset.Kind.VIDEO)
        self.assertIn(f'[Video: walkthrough.mp4](/lesson-assets/{asset.public_id}/)', lesson.content)
        response = self.client.get(reverse('lesson-detail', args=[self.course.id, lesson.id]))
        self.assertContains(response, 'lesson-content')
        self.assertContains(response, f'/lesson-assets/{asset.public_id}/')
        self.assertContains(response, '<video')

    def test_edit_form_has_no_separate_video_url_input(self):
        self.client.login(username='manager-a', password='test')

        response = self.client.get(reverse('lesson-update', args=[self.course.id, self.first.id]))

        self.assertContains(response, 'Add image or video')
        self.assertContains(response, 'lesson-media-files')
        self.assertNotContains(response, 'Optional video URL')

    def test_lesson_list_shows_title_and_description_without_content_preview(self):
        self.first.description = 'A concise summary.'
        self.first.content = 'Secret preview body text.'
        self.first.save()
        self.client.login(username='manager-a', password='test')

        response = self.client.get(reverse('lesson-list', args=[self.course.id]))

        self.assertContains(response, self.first.title)
        self.assertContains(response, 'A concise summary.')
        self.assertNotContains(response, 'Secret preview body text.')

    def test_lesson_can_accumulate_multiple_uploaded_videos_and_markdown_links(self):
        old_asset = LessonAsset.objects.create(
            lesson=self.first,
            kind=LessonAsset.Kind.VIDEO,
            mime_type='video/mp4',
            original_filename='old.mp4',
            file=SimpleUploadedFile('old.mp4', b'old video', content_type='video/mp4'),
        )
        self.client.login(username='manager-a', password='test')
        first_video = SimpleUploadedFile('new.webm', b'new video', content_type='video/webm')
        response = self.client.post(
            reverse('lesson-asset-upload', args=[self.course.id, self.first.id]),
            {'media_file': first_video, 'content': f'Updated lesson body.\n\n{old_asset.markdown_embed()}'},
        )
        self.assertEqual(response.status_code, 201)
        second_video = SimpleUploadedFile('another.mp4', b'another video', content_type='video/mp4')
        second_response = self.client.post(
            reverse('lesson-asset-upload', args=[self.course.id, self.first.id]),
            {'media_file': second_video, 'content': response.json()['content']},
        )
        self.assertEqual(second_response.status_code, 201)
        videos = LessonAsset.objects.filter(lesson=self.first, kind=LessonAsset.Kind.VIDEO)
        self.assertEqual(videos.count(), 3)
        self.assertTrue(LessonAsset.objects.filter(id=old_asset.id).exists())
        self.first.refresh_from_db()
        self.assertIn(f'[Video: old.mp4](/lesson-assets/{old_asset.public_id}/)', self.first.content)
        for video in videos.exclude(id=old_asset.id):
            self.assertIn(video.markdown_embed(), self.first.content)

        editor = self.client.get(reverse('lesson-update', args=[self.course.id, self.first.id]))
        self.assertContains(editor, str(old_asset.public_id))
        self.assertContains(editor, 'new.webm')

    def test_media_upload_is_rejected_for_unassigned_learner_and_invalid_image(self):
        self.client.login(username='manager-a', password='test')
        invalid_image = SimpleUploadedFile('bad.png', b'not-an-image', content_type='image/png')
        invalid_response = self.client.post(
            reverse('lesson-asset-upload', args=[self.course.id, self.first.id]),
            {'media_file': invalid_image, 'content': self.first.content},
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertFalse(LessonAsset.objects.filter(lesson=self.first).exists())

        self.client.force_login(self.unassigned_learner)
        denied = self.client.post(
            reverse('lesson-asset-upload', args=[self.course.id, self.first.id]),
            {'media_file': SimpleUploadedFile('movie.mp4', b'video'), 'content': ''},
        )
        self.assertEqual(denied.status_code, 404)


class LessonVideoValidationTests(TestCase):
    def setUp(self):
        tenant = Tenant.objects.create(name='Video Institute')
        admin = User.objects.create_user(
            username='video-admin', password='test', role=User.Role.TENANT_ADMIN, tenant=tenant
        )
        self.course = Course.objects.create(tenant=tenant, title='Video Course', creator=admin)

    def test_direct_https_video_url_uses_media_player(self):
        lesson = Lesson.objects.create(
            course=self.course,
            title='Video Lesson',
            content='Watch this.',
            video_url='https://media.example.test/course/lesson.mp4',
        )

        self.assertEqual(lesson.video_player, {
            'kind': 'media',
            'src': 'https://media.example.test/course/lesson.mp4',
        })

    def test_non_https_or_unrecognized_embed_url_is_rejected(self):
        for url in ('http://media.example.test/video.mp4', 'https://evil.example.test/embed/abc'):
            with self.subTest(url=url):
                lesson = Lesson(
                    course=self.course,
                    title=f'Invalid {url}',
                    content='Content',
                    video_url=url,
                )
                with self.assertRaises(ValidationError):
                    lesson.full_clean()
