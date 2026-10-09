from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Course, CourseAssignment, Lesson, Tenant, User


class LessonStudyViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Institute A')
        self.other_tenant = Tenant.objects.create(name='Institute B')
        self.tenant_admin = User.objects.create_user(
            username='manager-a', password='test', role=User.Role.TENANT_ADMIN, tenant=self.tenant
        )
        self.other_admin = User.objects.create_user(
            username='manager-b', password='test', role=User.Role.TENANT_ADMIN, tenant=self.other_tenant
        )
        self.learner = User.objects.create_user(
            username='learner-a', password='test', role=User.Role.TENANT_USER, tenant=self.tenant
        )
        self.unassigned_learner = User.objects.create_user(
            username='learner-unassigned', password='test', role=User.Role.TENANT_USER, tenant=self.tenant
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
