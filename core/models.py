from datetime import timedelta
import re
import uuid
from pathlib import PurePath
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone


def tenant_logo_upload_to(instance, filename):
    return f'organization-logos/{uuid.uuid4().hex}{PurePath(filename).suffix.lower()}'


def user_avatar_upload_to(instance, filename):
    return f'profile-avatars/{uuid.uuid4().hex}{PurePath(filename).suffix.lower()}'


class UserManager(DjangoUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        role = extra_fields.get('role', User.Role.TENANT_USER)
        if role != User.Role.TENANT_USER and 'must_change_password' not in extra_fields:
            extra_fields['must_change_password'] = False
        return super().create_user(username, email, password, **extra_fields)


class Tenant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        SUSPENDED = 'suspended', 'Suspended'

    class SubscriptionStatus(models.TextChoices):
        TRIAL = 'trial', 'Trial'
        SUBSCRIBED = 'subscribed', 'Subscribed'

    name = models.CharField(max_length=255, unique=True)
    brand_color = models.CharField(
        max_length=7,
        default='#09090b',
        validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Enter a 6-digit hex color.')],
    )
    address = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    support_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.FileField(
        upload_to=tenant_logo_upload_to,
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'gif', 'webp'])],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    trial_starts_at = models.DateTimeField(default=timezone.now)
    trial_ends_at = models.DateTimeField()
    expired_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                condition=Q(trial_ends_at__gt=models.F('trial_starts_at')),
                name='tenant_trial_ends_after_start',
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.trial_ends_at is None:
            self.trial_ends_at = self.trial_starts_at + timedelta(
                days=getattr(settings, 'DEFAULT_TRIAL_DAYS', 14)
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.trial_ends_at and self.trial_starts_at:
            if self.trial_ends_at <= self.trial_starts_at:
                raise ValidationError('Trial end must be after trial start.')

    def is_trial_expired(self, at_time=None):
        at_time = at_time or timezone.now()
        return (
            self.subscription_status == self.SubscriptionStatus.TRIAL
            and at_time >= self.trial_ends_at
        )

    def mark_expired(self, at_time=None):
        at_time = at_time or timezone.now()
        if self.subscription_status != self.SubscriptionStatus.TRIAL:
            return
        if self.status != self.Status.EXPIRED:
            self.status = self.Status.EXPIRED
            self.expired_at = at_time
            self.save(update_fields=['status', 'expired_at', 'updated_at'])

    def reactivate(self, at_time=None):
        at_time = at_time or timezone.now()
        self.subscription_status = self.SubscriptionStatus.TRIAL
        self.status = self.Status.ACTIVE
        self.trial_starts_at = at_time
        self.trial_ends_at = at_time + timedelta(days=getattr(settings, 'DEFAULT_TRIAL_DAYS', 14))
        self.expired_at = None
        self.save(update_fields=[
            'subscription_status', 'status', 'trial_starts_at', 'trial_ends_at', 'expired_at', 'updated_at'
        ])


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        SUPER_VIEWER = 'super_viewer', 'Super Viewer'
        TENANT_ADMIN = 'tenant_admin', 'Tenant Admin'
        TENANT_USER = 'tenant_user', 'Tenant User'

    PLATFORM_ROLES = {
        Role.SUPER_ADMIN,
        Role.ADMIN,
        Role.SUPER_VIEWER,
    }
    TENANT_ROLES = {
        Role.TENANT_ADMIN,
        Role.TENANT_USER,
    }

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.TENANT_USER)
    must_change_password = models.BooleanField(default=True)
    avatar = models.FileField(
        upload_to=user_avatar_upload_to,
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'gif', 'webp'])],
    )
    tenant = models.ForeignKey(
        Tenant,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='users',
    )
    objects = UserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        role__in=[
                            'super_admin',
                            'admin',
                            'super_viewer',
                        ],
                        tenant__isnull=True,
                    )
                    | Q(
                        role__in=[
                            'tenant_admin',
                            'tenant_user',
                        ],
                        tenant__isnull=False,
                    )
                ),
                name='user_role_tenant_membership_valid',
            ),
        ]

    def clean(self):
        super().clean()
        if self.role in self.PLATFORM_ROLES and self.tenant_id is not None:
            raise ValidationError('Platform users must not be assigned to a tenant.')
        if self.role in self.TENANT_ROLES and self.tenant_id is None:
            raise ValidationError('Tenant users must be assigned to a tenant.')

    def save(self, *args, **kwargs):
        if self.is_superuser and self.tenant_id is None and self.role == self.Role.TENANT_USER:
            self.role = self.Role.SUPER_ADMIN
        self.full_clean()
        super().save(*args, **kwargs)


class Course(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_courses',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'title'], name='unique_course_title_per_tenant'),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.creator_id and self.creator.role in User.TENANT_ROLES:
            if self.creator.tenant_id != self.tenant_id:
                raise ValidationError('Course creator must belong to the same tenant as the course.')
        if self.creator_id and self.creator.role == User.Role.TENANT_USER:
            raise ValidationError('Learners cannot create courses.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, max_length=500)
    content = models.TextField()
    video_url = models.URLField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        constraints = [
            models.UniqueConstraint(fields=['course', 'order'], name='unique_lesson_order_per_course'),
            models.UniqueConstraint(fields=['course', 'title'], name='unique_lesson_title_per_course'),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if not self.video_url:
            return
        parsed = urlsplit(self.video_url)
        host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https' or not host:
            raise ValidationError({'video_url': 'Video URLs must use HTTPS.'})
        if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'}:
            video_id = self._youtube_video_id(parsed)
            if not video_id:
                raise ValidationError({'video_url': 'Enter a valid YouTube video URL.'})
            return
        if host in {'vimeo.com', 'www.vimeo.com', 'player.vimeo.com'}:
            if not self._vimeo_video_id(parsed):
                raise ValidationError({'video_url': 'Enter a valid Vimeo video URL.'})
            return
        if parsed.path.lower().endswith(('.mp4', '.webm', '.ogg')):
            return
        raise ValidationError(
            {'video_url': 'Use a YouTube/Vimeo link or a direct MP4, WebM, or Ogg video URL.'}
        )

    @staticmethod
    def _youtube_video_id(parsed):
        host = (parsed.hostname or '').lower()
        if host == 'youtu.be':
            video_id = parsed.path.strip('/').split('/')[0]
        elif parsed.path.startswith(('/embed/', '/shorts/')):
            parts = parsed.path.strip('/').split('/')
            video_id = parts[1] if len(parts) > 1 else ''
        else:
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        return video_id if re.fullmatch(r'[A-Za-z0-9_-]{6,20}', video_id) else None

    @staticmethod
    def _vimeo_video_id(parsed):
        match = re.fullmatch(r'(?:video/)?(\d+)', parsed.path.strip('/'))
        return match.group(1) if match else None

    @property
    def video_player(self):
        """Return a validated player descriptor suitable for an iframe/video tag."""
        if not self.video_url:
            return None
        parsed = urlsplit(self.video_url)
        host = (parsed.hostname or '').lower()
        if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'}:
            video_id = self._youtube_video_id(parsed)
            if video_id:
                return {'kind': 'embed', 'src': f'https://www.youtube-nocookie.com/embed/{video_id}'}
        elif host in {'vimeo.com', 'www.vimeo.com', 'player.vimeo.com'}:
            video_id = self._vimeo_video_id(parsed)
            if video_id:
                return {'kind': 'embed', 'src': f'https://player.vimeo.com/video/{video_id}'}
        elif parsed.scheme == 'https' and parsed.path.lower().endswith(('.mp4', '.webm', '.ogg')):
            return {'kind': 'media', 'src': self.video_url}
        return None

    def save(self, *args, **kwargs):
        if self._state.adding:
            with transaction.atomic():
                # Serialize lesson inserts/reorders for this course on databases
                # that support row-level locks. The unique constraint remains
                # the final guard against duplicate order values.
                Course.objects.select_for_update().get(pk=self.course_id)
                current_max = (
                    Lesson.objects.filter(course_id=self.course_id).aggregate(max_order=Max('order'))['max_order']
                    or 0
                )
                order_taken = Lesson.objects.filter(
                    course_id=self.course_id,
                    order=self.order,
                ).exists()
                if self.order is None or self.order <= 0 or order_taken:
                    self.order = current_max + 1
                self.full_clean()
                super().save(*args, **kwargs)
            return

        self.full_clean()
        super().save(*args, **kwargs)


def lesson_asset_upload_to(instance, filename):
    extension = PurePath(filename).suffix.lower()
    return f'lesson-assets/{instance.public_id.hex}{extension}'


class LessonAsset(models.Model):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assets')
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    file = models.FileField(upload_to=lesson_asset_upload_to)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    mime_type = models.CharField(max_length=50)
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at', 'id']

    def __str__(self):
        return f'{self.kind} for {self.lesson}'

    def markdown_embed(self):
        url = f'/lesson-assets/{self.public_id}/'
        if self.kind == self.Kind.IMAGE:
            image_name = PurePath(self.original_filename or self.file.name).stem.replace('[', '(').replace(']', ')')
            return f'![{image_name}]({url})'
        filename = (self.original_filename or PurePath(self.file.name).name).replace('[', '(').replace(']', ')')
        return f'[Video: {filename}]({url})'

    def clean(self):
        super().clean()
        from .media import LESSON_UPLOAD_TYPES

        if self.file:
            expected = LESSON_UPLOAD_TYPES.get(PurePath(self.file.name).suffix.lower())
            if not expected or expected != (self.kind, self.mime_type):
                raise ValidationError('Uploaded media type does not match its permitted file extension.')


class CourseAssignment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='course_assignments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    learner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'course', 'learner'],
                name='unique_course_assignment_per_learner',
            ),
        ]

    def __str__(self):
        return f'{self.learner} assigned to {self.course}'

    def clean(self):
        super().clean()
        if self.course_id and self.tenant_id and self.course.tenant_id != self.tenant_id:
            raise ValidationError('Assigned course must belong to the assignment tenant.')
        if self.learner_id:
            if self.learner.role != User.Role.TENANT_USER:
                raise ValidationError('Only tenant users can be assigned to courses.')
            if not self.learner.is_active:
                raise ValidationError('Inactive learners cannot be assigned to courses.')
            if self.tenant_id and self.learner.tenant_id != self.tenant_id:
                raise ValidationError('Assigned learner must belong to the assignment tenant.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class LessonProgress(models.Model):
    assignment = models.ForeignKey(
        CourseAssignment,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_records')
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['lesson__order', 'lesson__title']
        constraints = [
            models.UniqueConstraint(fields=['assignment', 'lesson'], name='unique_progress_per_assignment_lesson'),
        ]

    def __str__(self):
        return f'{self.assignment.learner} progress for {self.lesson}'

    def clean(self):
        super().clean()
        if self.assignment_id and self.lesson_id:
            if self.assignment.course_id != self.lesson.course_id:
                raise ValidationError('Progress lesson must belong to the assigned course.')

    def save(self, *args, **kwargs):
        if self.is_complete and self.completed_at is None:
            self.completed_at = timezone.now()
        if not self.is_complete:
            self.completed_at = None
        self.full_clean()
        super().save(*args, **kwargs)
