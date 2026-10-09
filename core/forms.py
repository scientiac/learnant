from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.text import slugify

from .models import Course, CourseAssignment, Lesson, Tenant, User


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
        fields = ['title', 'content', 'video_url', 'order']
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
            'video_url': forms.URLInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'https://youtu.be/... or https://example.org/video.mp4',
                }
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
        # Creation may leave order blank to request automatic append ordering;
        # editing must keep an explicit positive position.
        self.fields['order'].required = bool(self.instance.pk)


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
        if User.objects.filter(username=username).exists():
            raise ValidationError('This username is already taken.')
        return username

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
                password=self.cleaned_data['password1'],
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
                role=User.Role.TENANT_ADMIN,
                tenant=tenant,
            )
        return user


class TenantSettingsForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['name', 'brand_color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'brand_color': forms.TextInput(
                attrs={'class': 'form-input', 'type': 'color', 'aria-label': 'Organization brand color'}
            ),
        }


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'}),
        }


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
