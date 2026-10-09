from django import forms

from .models import Course, CourseAssignment, Lesson, User


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'w-full rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none',
                    'placeholder': 'Course title',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'w-full rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none',
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
                    'class': 'w-full rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none',
                    'placeholder': 'Lesson title',
                }
            ),
            'content': forms.Textarea(
                attrs={
                    'class': 'w-full rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none',
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
            {'class': 'w-full rounded-md border border-slate-300 px-3 py-2'}
        )
