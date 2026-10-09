from django import forms

from .models import Course


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
