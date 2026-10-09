from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseForm, LessonForm
from .models import Course, Lesson, Tenant, User
from .permissions import (
    can_manage_platform,
    can_mutate_tenant_data,
    can_read_platform,
    can_reactivate_tenant,
    is_tenant_admin,
)


def health_check(request):
    return JsonResponse({'status': 'ok'})


@login_required
def dashboard(request):
    user = request.user
    context = {
        'can_manage_platform': can_manage_platform(user),
        'can_read_platform': can_read_platform(user),
        'can_reactivate_tenant': can_reactivate_tenant(user),
        'tenant_count': None,
        'tenant_user_count': None,
    }

    if user.role in {User.Role.SUPER_ADMIN, User.Role.ADMIN, User.Role.SUPER_VIEWER}:
        context['tenant_count'] = Tenant.objects.count()
    elif user.tenant_id:
        context['tenant_user_count'] = User.objects.filter(tenant=user.tenant).count()

    return render(request, 'core/dashboard.html', context)


@login_required
def course_list(request):
    user = request.user
    courses = Course.objects.select_related('tenant', 'creator')

    if user.role in {User.Role.SUPER_ADMIN, User.Role.ADMIN, User.Role.SUPER_VIEWER}:
        visible_courses = courses
    elif user.role == User.Role.TENANT_ADMIN and user.tenant_id:
        visible_courses = courses.filter(tenant=user.tenant)
    else:
        visible_courses = Course.objects.none()

    return render(
        request,
        'core/course_list.html',
        {
            'courses': visible_courses,
            'can_create_courses': user.role == User.Role.TENANT_ADMIN
            and user.tenant
            and user.tenant.status == Tenant.Status.ACTIVE,
        },
    )


@login_required
def course_create(request):
    user = request.user
    if not is_tenant_admin(user):
        return HttpResponseForbidden('Only tenant admins can create courses.')
    if not can_mutate_tenant_data(user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.tenant = user.tenant
            course.creator = user
            course.save()
            return redirect('course-list')
    else:
        form = CourseForm()

    return render(request, 'core/course_form.html', {'form': form})


def visible_courses_for_user(user):
    courses = Course.objects.select_related('tenant', 'creator')
    if user.role in {User.Role.SUPER_ADMIN, User.Role.ADMIN, User.Role.SUPER_VIEWER}:
        return courses
    if user.role == User.Role.TENANT_ADMIN and user.tenant_id:
        return courses.filter(tenant=user.tenant)
    return Course.objects.none()


@login_required
def lesson_list(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    lessons = Lesson.objects.filter(course=course)
    return render(
        request,
        'core/lesson_list.html',
        {
            'course': course,
            'lessons': lessons,
            'can_create_lessons': request.user.role == User.Role.TENANT_ADMIN
            and request.user.tenant_id == course.tenant_id
            and course.tenant.status == Tenant.Status.ACTIVE,
        },
    )


@login_required
def lesson_create(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can create lessons for their own courses.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()
            return redirect('lesson-list', course_id=course.id)
    else:
        form = LessonForm()

    return render(request, 'core/lesson_form.html', {'course': course, 'form': form})
