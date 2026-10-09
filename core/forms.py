import calendar
from datetime import timedelta

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import validate_email
from django.utils.text import slugify

from .models import Course, CourseAssignment, Lesson, Tenant, User
from .media import MAX_VIDEO_SIZE, classify_lesson_upload, validate_image_upload


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(file, initial) for file in files]


class CourseForm(forms.ModelForm):
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.none(),
        widget=forms.Select(attrs={'class': 'form-input'}),
        required=False,
    )

    class Meta:
        model = Course
        fields = ['title', 'description', 'tenant']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Course title',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Short course description',
                    'rows': 4,
                }
            ),
        }

    def __init__(self, *args, platform_tenant_management=False, **kwargs):
        super().__init__(*args, **kwargs)
        if platform_tenant_management:
            from django.utils import timezone

            self.fields['tenant'].queryset = Tenant.objects.filter(
                status=Tenant.Status.ACTIVE,
                trial_ends_at__gt=timezone.now(),
            )
            self.fields['tenant'].required = True
        else:
            self.fields.pop('tenant')


class LessonForm(forms.ModelForm):
    order = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={'class': 'form-input', 'min': 1, 'step': 1}
        ),
    )

    class Meta:
        model = Lesson
        fields = ['title', 'description', 'content', 'order']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Lesson title',
                }
            ),
            'content': forms.Textarea(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Lesson content',
                    'rows': 8,
                }
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Short lesson summary'}
            ),
            'order': forms.NumberInput(
                attrs={
                    'class': 'w-32 rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none',
                    'min': 1,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['media_files'] = MultipleFileField(
            required=False,
            widget=MultipleFileInput(
                attrs={
                    'class': 'form-input',
                    'multiple': True,
                    'accept': 'image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm,video/ogg',
                }
            ),
            label='Upload images or a video to insert into the Markdown content',
        )
        self.fields['remove_video'] = forms.BooleanField(
            required=False,
            label='Remove the existing uploaded video',
            widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        )
        # Creation may leave order blank to request automatic append ordering;
        # editing must keep an explicit positive position.
        self.fields['order'].required = bool(self.instance.pk)

    def clean_media_files(self):
        uploads = self.cleaned_data.get('media_files', [])
        if len(uploads) > 10:
            raise ValidationError('Upload at most 10 files per lesson.')
        if sum(upload.size for upload in uploads) > MAX_VIDEO_SIZE:
            raise ValidationError('Combined lesson uploads must not exceed 100 MB.')
        videos = 0
        errors = []
        for upload in uploads:
            try:
                kind, _mime_type = classify_lesson_upload(upload)
            except ValidationError as error:
                errors.extend(error.messages)
                continue
            videos += kind == 'video'
        if videos > 1:
            errors.append('A lesson may contain at most one video.')
        if errors:
            raise ValidationError(errors)
        return uploads

    def clean(self):
        cleaned = super().clean()
        uploads = cleaned.get('media_files', [])
        has_video_upload = any(classify_lesson_upload(upload)[0] == 'video' for upload in uploads)
        if (
            has_video_upload
            and self.instance.pk
            and self.instance.assets.filter(kind='video').exists()
            and not cleaned.get('remove_video')
        ):
            self.add_error('media_files', 'Select “Remove the existing uploaded video” to replace it.')
        return cleaned


class CourseAssignmentForm(forms.ModelForm):
    class Meta:
        model = CourseAssignment
        fields = ['learner']

    def __init__(self, *args, tenant, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['learner'].queryset = User.objects.filter(
            role=User.Role.TENANT_USER,
            tenant=tenant,
        ).order_by('username')
        self.fields['learner'].widget.attrs.update(
            {'class': 'form-input'}
        )


class TenantSignupForm(forms.Form):
    """Public sign-up form that creates a new Tenant and a Tenant Admin user."""

    org_name = forms.CharField(
        max_length=255,
        label='Organisation name',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Acme Institute of Learning'}),
    )
    username = forms.CharField(
        max_length=150,
        label='Username',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'jane_admin', 'autocomplete': 'username'}),
    )
    email = forms.EmailField(
        max_length=254,
        label='Admin email',
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'jane@example.org', 'autocomplete': 'email'}),
    )
    first_name = forms.CharField(
        max_length=150,
        label='First name',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Jane', 'autocomplete': 'given-name'}),
    )
    last_name = forms.CharField(
        max_length=150,
        label='Last name',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Smith', 'autocomplete': 'family-name'}),
    )
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'autocomplete': 'new-password'}),
    )

    def clean_org_name(self):
        name = self.cleaned_data['org_name'].strip()
        if Tenant.objects.filter(name__iexact=name).exists():
            raise ValidationError('An organisation with this name already exists.')
        return name

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already in use.')
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned_data

    def save(self):
        """Create the Tenant and Tenant Admin atomically. Returns the new User."""
        from django.db import transaction

        with transaction.atomic():
            tenant = Tenant.objects.create(name=self.cleaned_data['org_name'])
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password1'],
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
                role=User.Role.TENANT_ADMIN,
                must_change_password=False,
                tenant=tenant,
            )
        return user


class TenantSettingsForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['name', 'brand_color', 'logo', 'address', 'contact_phone', 'support_email', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'brand_color': forms.TextInput(
                attrs={'class': 'form-input', 'type': 'color', 'aria-label': 'Organization brand color'}
            ),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/png,image/jpeg,image/gif,image/webp'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'tel'}),
            'support_email': forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'}),
            'website': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://example.org'}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if isinstance(logo, UploadedFile):
            validate_image_upload(logo)
        return logo


class TenantSubscriptionForm(forms.Form):
    subscription_status = forms.ChoiceField(
        choices=Tenant.SubscriptionStatus.choices,
        widget=forms.Select(attrs={'class': 'form-input'}),
    )
    expiration_mode = forms.ChoiceField(
        choices=[('exact', 'Set exact trial end'), ('adjust', 'Adjust current trial end')],
        widget=forms.Select(attrs={'class': 'form-input'}),
    )
    trial_ends_at = forms.DateTimeField(
        required=False,
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S%z'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'class': 'form-input', 'type': 'datetime-local'},
        ),
    )
    adjustment_amount = forms.IntegerField(
        required=False,
        min_value=-100000,
        max_value=100000,
        widget=forms.NumberInput(attrs={'class': 'form-input'}),
        help_text='Use a positive or negative number.',
    )
    adjustment_unit = forms.ChoiceField(
        required=False,
        choices=[('', 'Choose a unit'), ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('months', 'Months')],
        widget=forms.Select(attrs={'class': 'form-input'}),
    )

    def __init__(self, *args, tenant, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        self.initial.setdefault('subscription_status', tenant.subscription_status)
        self.initial.setdefault('expiration_mode', 'exact')
        self.initial.setdefault('trial_ends_at', tenant.trial_ends_at)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('subscription_status') != Tenant.SubscriptionStatus.TRIAL:
            return cleaned

        mode = cleaned.get('expiration_mode')
        if mode == 'exact':
            end_time = cleaned.get('trial_ends_at')
            if not end_time:
                self.add_error('trial_ends_at', 'Enter the exact trial expiration date and time.')
                return cleaned
        elif mode == 'adjust':
            amount = cleaned.get('adjustment_amount')
            unit = cleaned.get('adjustment_unit')
            if amount is None or not unit:
                self.add_error(None, 'Enter both an adjustment amount and unit.')
                return cleaned
            if amount == 0:
                self.add_error('adjustment_amount', 'Adjustment must not be zero.')
                return cleaned
            try:
                end_time = self._adjust_expiration(self.tenant.trial_ends_at, amount, unit)
            except (OverflowError, ValueError):
                self.add_error('adjustment_amount', 'The adjusted expiration date is out of range.')
                return cleaned
        else:
            self.add_error('expiration_mode', 'Choose how to update the trial expiration.')
            return cleaned

        if end_time <= self.tenant.trial_starts_at:
            self.add_error(None, 'Trial expiration must be after its start date.')
            return cleaned
        cleaned['resolved_trial_ends_at'] = end_time
        return cleaned

    @staticmethod
    def _adjust_expiration(value, amount, unit):
        if unit == 'minutes':
            return value + timedelta(minutes=amount)
        if unit == 'hours':
            return value + timedelta(hours=amount)
        if unit == 'days':
            return value + timedelta(days=amount)

        month_index = value.year * 12 + (value.month - 1) + amount
        year, month_zero_based = divmod(month_index, 12)
        month = month_zero_based + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'}),
            'avatar': forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/png,image/jpeg,image/gif,image/webp'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['remove_avatar'] = forms.BooleanField(
            required=False,
            label='Remove current profile image',
            widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        )

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if isinstance(avatar, UploadedFile):
            validate_image_upload(avatar)
        return avatar


class TenantUserManagementForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class PlatformAccountProvisionForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(max_length=254, widget=forms.EmailInput(attrs={'class': 'form-input'}))
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    role = forms.ChoiceField(
        choices=[(User.Role.ADMIN, 'Admin'), (User.Role.SUPER_VIEWER, 'Super Viewer')],
        widget=forms.Select(attrs={'class': 'form-input'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already in use.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already in use.')
        return email


class BulkStudentOnboardingForm(forms.Form):
    students = forms.CharField(
        label='Student usernames or email addresses',
        widget=forms.Textarea(
            attrs={
                'class': 'form-input',
                'rows': 8,
                'placeholder': 'alex\nstudent@example.org',
            }
        ),
    )

    def __init__(self, *args, tenant, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)

    def clean_students(self):
        lines = [line.strip() for line in self.cleaned_data['students'].splitlines() if line.strip()]
        if not lines:
            raise ValidationError('Enter at least one username or email address.')
        if len(lines) > 100:
            raise ValidationError('You can onboard at most 100 students at a time.')

        normalized_inputs = set()
        usernames = set()
        emails = set()
        students = []
        errors = []

        for line_number, value in enumerate(lines, start=1):
            normalized = value.casefold()
            if normalized in normalized_inputs:
                errors.append(f'Line {line_number}: duplicate entry "{value}".')
                continue
            normalized_inputs.add(normalized)

            if '@' in value:
                try:
                    validate_email(value)
                except ValidationError:
                    errors.append(f'Line {line_number}: "{value}" is not a valid email address.')
                    continue
                email_key = value.casefold()
                if email_key in emails or User.objects.filter(email__iexact=value).exists():
                    errors.append(f'Line {line_number}: email "{value}" is already in use.')
                    continue

                base_username = (slugify(value.split('@', 1)[0]) or 'learner')[:140]
                username = base_username
                suffix = 1
                while username.casefold() in usernames or User.objects.filter(username__iexact=username).exists():
                    suffix += 1
                    username = f'{base_username[:140 - len(str(suffix))]}{suffix}'
                emails.add(email_key)
                usernames.add(username.casefold())
                students.append({'username': username, 'email': value})
            else:
                if len(value) > 150:
                    errors.append(f'Line {line_number}: usernames must be 150 characters or fewer.')
                    continue
                try:
                    User._meta.get_field('username').run_validators(value)
                except ValidationError:
                    errors.append(f'Line {line_number}: "{value}" is not a valid username.')
                    continue
                if normalized in usernames or User.objects.filter(username__iexact=value).exists():
                    errors.append(f'Line {line_number}: username "{value}" is already in use.')
                    continue
                usernames.add(normalized)
                students.append({'username': value, 'email': ''})

        if errors:
            raise ValidationError(errors)
        return students


class StudentCsvImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Learner CSV file',
        widget=forms.ClearableFileInput(
            attrs={'class': 'form-input', 'accept': '.csv,text/csv'}
        ),
    )

    def clean_csv_file(self):
        upload = self.cleaned_data['csv_file']
        if not upload.name.lower().endswith('.csv'):
            raise ValidationError('Choose a .csv file.')
        if upload.size > 5 * 1024 * 1024:
            raise ValidationError('CSV files must be 5 MB or smaller.')
        return upload


class StudentEnrollmentRowForm(forms.Form):
    username = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username'}),
    )
    email = forms.EmailField(
        required=False,
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'learner@example.org'}),
    )
    first_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First name'}),
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last name'}),
    )
    courses = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Course.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'course-choice-list'}),
        label='Assign courses (optional)',
    )

    def __init__(self, *args, tenant, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['courses'].queryset = Course.objects.filter(tenant=tenant).order_by('id')
        self.fields['courses'].label_from_instance = lambda course: f'#{course.id} — {course.title}'

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username:
            User._meta.get_field('username').run_validators(username)
        return username

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('username') and not cleaned.get('email'):
            if any(cleaned.get(field) for field in ('first_name', 'last_name', 'courses')):
                raise ValidationError('Provide a username or email for this learner row.')
        return cleaned


StudentEnrollmentFormSet = forms.formset_factory(
    StudentEnrollmentRowForm,
    extra=1,
    max_num=100,
    validate_max=True,
    absolute_max=100,
    can_delete=True,
)


class CourseAssistantPreviewForm(forms.Form):
    learner_role = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Junior analyst'}),
    )
    current_level = forms.ChoiceField(
        choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')],
        widget=forms.Select(attrs={'class': 'form-input'}),
    )
    goal = forms.CharField(
        max_length=240,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Build and present a data dashboard'}),
    )
    hours_per_week = forms.DecimalField(
        min_value=0.5,
        max_value=80,
        decimal_places=1,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '0.5', 'max': '80', 'step': '0.5'}),
    )
    duration_weeks = forms.IntegerField(
        min_value=1,
        max_value=52,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 52}),
    )
