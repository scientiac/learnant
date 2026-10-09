"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from core.views import (
    assignment_create,
    assignment_list,
    course_create,
    course_list,
    dashboard,
    health_check,
    lesson_create,
    lesson_list,
    lesson_mark_complete,
    progress_list,
)

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('courses/', course_list, name='course-list'),
    path('courses/new/', course_create, name='course-create'),
    path('courses/<int:course_id>/lessons/', lesson_list, name='lesson-list'),
    path('courses/<int:course_id>/lessons/new/', lesson_create, name='lesson-create'),
    path('courses/<int:course_id>/assignments/', assignment_list, name='assignment-list'),
    path('courses/<int:course_id>/assignments/new/', assignment_create, name='assignment-create'),
    path('courses/<int:course_id>/progress/', progress_list, name='progress-list'),
    path(
        'courses/<int:course_id>/lessons/<int:lesson_id>/complete/',
        lesson_mark_complete,
        name='lesson-mark-complete',
    ),
    path('health/', health_check, name='health-check'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
]
