import secrets

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from .forms import (
    CourseAssignmentForm,
    BulkStudentOnboardingForm,
    CourseForm,
    LessonForm,
    ProfileSettingsForm,
    TenantSettingsForm,
    TenantSignupForm,
)
from .models import Course, CourseAssignment, Lesson, LessonProgress, Tenant, User
from .permissions import (
    can_manage_platform,
    can_mutate_tenant_data,
    can_read_platform,
    can_reactivate_tenant,
    is_platform_user,
    is_tenant_admin,
    is_tenant_user,
)


def health_check(request):
    return JsonResponse({'status': 'ok'})


def about(request):
    """Hosted documentation & platform architecture details."""
    return render(request, 'core/about.html')


def landing(request):
    """Public entry page; never expose the protected dashboard anonymously."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing.html')


def signup(request):
    """Public sign-up: creates a new Tenant and a Tenant Admin account."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = TenantSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import login as auth_login
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('dashboard')
    else:
        form = TenantSignupForm()
    features = [
        'Tenant-isolated course management',
        'Role-based access control',
        'Learner progress tracking',
        '14-day trial — no card needed',
    ]
    return render(request, 'registration/signup.html', {'form': form, 'features': features})

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
    visible_courses = visible_courses_for_user(user)

    return render(
        request,
        'core/course_list.html',
        {
            'courses': visible_courses,
            'can_create_courses': user.role == User.Role.TENANT_ADMIN
            and user.tenant
            and can_mutate_tenant_data(user),
        },
    )


@login_required
def tenant_list(request):
    if not is_platform_user(request.user):
        return HttpResponseForbidden('Only platform users can view tenants.')
    tenants = Tenant.objects.all()
    return render(
        request,
        'core/tenant_list.html',
        {'tenants': tenants, 'can_reactivate_tenants': can_reactivate_tenant(request.user)},
    )


@login_required
def tenant_reactivate(request, tenant_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Reactivation must use POST.')
    if not can_reactivate_tenant(request.user):
        return HttpResponseForbidden('Only Super Admin can reactivate tenants.')
    tenant = get_object_or_404(Tenant, id=tenant_id)
    tenant.reactivate()
    return redirect('tenant-list')


@login_required
def organization_settings(request):
    user = request.user
    if not is_tenant_admin(user) or not user.tenant_id:
        return HttpResponseForbidden('Only tenant admins can manage organization settings.')
    if not can_mutate_tenant_data(user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = TenantSettingsForm(request.POST, instance=user.tenant)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = TenantSettingsForm(instance=user.tenant)
    return render(request, 'core/organization_settings.html', {'form': form})


@login_required
def profile_settings(request):
    user = request.user
    if user.role in User.TENANT_ROLES and not can_mutate_tenant_data(user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = ProfileSettingsForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProfileSettingsForm(instance=user)
    return render(request, 'core/profile_settings.html', {'form': form})


@login_required
@never_cache
def bulk_student_add(request):
    user = request.user
    if not is_tenant_admin(user) or not user.tenant_id:
        return HttpResponseForbidden('Only tenant admins can onboard students.')
    if not can_mutate_tenant_data(user):
        return HttpResponseForbidden('This tenant is read-only.')

    created_students = []
    if request.method == 'POST':
        form = BulkStudentOnboardingForm(request.POST, tenant=user.tenant)
        if form.is_valid():
            with transaction.atomic():
                for student_data in form.cleaned_data['students']:
                    initial_password = secrets.token_urlsafe(12)
                    student = User.objects.create_user(
                        username=student_data['username'],
                        email=student_data['email'],
                        password=initial_password,
                        role=User.Role.TENANT_USER,
                        tenant=user.tenant,
                    )
                    created_students.append(
                        {'username': student.username, 'email': student.email, 'password': initial_password}
                    )
    else:
        form = BulkStudentOnboardingForm(tenant=user.tenant)

    return render(
        request,
        'core/bulk_student_add.html',
        {'form': form, 'created_students': created_students},
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


@login_required
def course_update(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can update their own courses.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            updated_course = form.save(commit=False)
            updated_course.tenant = course.tenant
            updated_course.creator = course.creator
            updated_course.save()
            return redirect('course-list')
    else:
        form = CourseForm(instance=course)

    return render(request, 'core/course_form.html', {'form': form, 'course': course})


@login_required
def course_delete(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can delete their own courses.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')
    if request.method != 'POST':
        return render(request, 'core/confirm_delete.html', {'object': course, 'cancel_url': 'course-list'})

    course.delete()
    return redirect('course-list')


def visible_courses_for_user(user):
    courses = Course.objects.select_related('tenant', 'creator')
    if user.role in {User.Role.SUPER_ADMIN, User.Role.ADMIN, User.Role.SUPER_VIEWER}:
        return courses
    if user.role == User.Role.TENANT_ADMIN and user.tenant_id:
        return courses.filter(tenant=user.tenant)
    if user.role == User.Role.TENANT_USER and user.tenant_id:
        return courses.filter(assignments__learner=user).distinct()
    return Course.objects.none()


@login_required
def lesson_list(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    lessons = Lesson.objects.filter(course=course)
    assignment = None
    progress_by_lesson = {}
    if is_tenant_user(request.user):
        assignment = get_object_or_404(CourseAssignment, course=course, learner=request.user)
        progress_by_lesson = {
            progress.lesson_id: progress
            for progress in LessonProgress.objects.filter(assignment=assignment)
        }
    lesson_items = [
        {'lesson': lesson, 'progress': progress_by_lesson.get(lesson.id)}
        for lesson in lessons
    ]
    return render(
        request,
        'core/lesson_list.html',
        {
            'course': course,
            'lesson_items': lesson_items,
            'assignment': assignment,
            'can_create_lessons': request.user.role == User.Role.TENANT_ADMIN
            and request.user.tenant_id == course.tenant_id
            and can_mutate_tenant_data(request.user),
            'can_update_progress': bool(
                assignment and course.tenant.status == Tenant.Status.ACTIVE
            ),
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


@login_required
def lesson_update(request, course_id, lesson_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can update lessons for their own courses.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            updated_lesson = form.save(commit=False)
            updated_lesson.course = course
            updated_lesson.save()
            return redirect('lesson-list', course_id=course.id)
    else:
        form = LessonForm(instance=lesson)

    return render(request, 'core/lesson_form.html', {'course': course, 'lesson': lesson, 'form': form})


@login_required
def lesson_delete(request, course_id, lesson_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can delete lessons for their own courses.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')
    if request.method != 'POST':
        return render(
            request,
            'core/confirm_delete.html',
            {'object': lesson, 'cancel_url': 'lesson-list', 'cancel_url_arg': course.id},
        )

    lesson.delete()
    return redirect('lesson-list', course_id=course.id)


@login_required
def assignment_list(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can view course assignments.')
    assignments = CourseAssignment.objects.select_related('learner').filter(course=course)
    return render(
        request,
        'core/assignment_list.html',
        {
            'course': course,
            'assignments': assignments,
            'can_create_assignments': can_mutate_tenant_data(request.user),
        },
    )


@login_required
def assignment_create(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can assign their own courses.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = CourseAssignmentForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.tenant = request.user.tenant
            assignment.course = course
            assignment.save()
            return redirect('assignment-list', course_id=course.id)
    else:
        form = CourseAssignmentForm(tenant=request.user.tenant)

    return render(request, 'core/assignment_form.html', {'course': course, 'form': form})


@login_required
def assignment_delete(request, course_id, assignment_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can revoke their own course assignments.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')
    assignment = get_object_or_404(CourseAssignment, id=assignment_id, course=course, tenant=request.user.tenant)
    if request.method != 'POST':
        return render(
            request,
            'core/confirm_delete.html',
            {'object': assignment, 'cancel_url': 'assignment-list', 'cancel_url_arg': course.id},
        )

    assignment.delete()
    return redirect('assignment-list', course_id=course.id)


@login_required
def lesson_mark_complete(request, course_id, lesson_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Progress updates must use POST.')
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_user(request.user):
        return HttpResponseForbidden('Only learners can update their own progress.')
    if not can_mutate_tenant_data(request.user):
        return HttpResponseForbidden('This tenant is read-only.')
    assignment = get_object_or_404(CourseAssignment, course=course, learner=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    progress, _ = LessonProgress.objects.get_or_create(assignment=assignment, lesson=lesson)
    progress.is_complete = True
    progress.save()
    return redirect('lesson-list', course_id=course.id)


@login_required
def progress_list(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not is_tenant_admin(request.user) or request.user.tenant_id != course.tenant_id:
        return HttpResponseForbidden('Only tenant admins can view course progress.')
    assignments = CourseAssignment.objects.select_related('learner').filter(course=course)
    progress_records = LessonProgress.objects.select_related('assignment__learner', 'lesson').filter(
        assignment__course=course
    )
    return render(
        request,
        'core/progress_list.html',
        {'course': course, 'assignments': assignments, 'progress_records': progress_records},
    )
