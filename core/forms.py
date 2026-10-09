from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Course, CourseAssignment, Lesson, Tenant, User


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description']
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


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'content', 'order']
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
            'order': forms.NumberInput(
                attrs={
                    'class': 'w-32 rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none',
                    'min': 1,
                }
            ),
        }


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
