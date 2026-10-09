import secrets

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.db.models import Max
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .forms import (
    CourseAssignmentForm,
    BulkStudentOnboardingForm,
    CourseForm,
    CourseAssistantPreviewForm,
    LessonForm,
    PlatformAccountProvisionForm,
    ProfileSettingsForm,
    StudentCsvImportForm,
    TenantSubscriptionForm,
    TenantSettingsForm,
    TenantSignupForm,
    TenantUserManagementForm,
)
from .media import classify_lesson_upload, image_mime_type
from .csv_enrollment import blank_enrollment_csv, import_student_csv
from .models import Course, CourseAssignment, Lesson, LessonAsset, LessonProgress, Tenant, User
from .permissions import (
    can_manage_platform,
    can_manage_tenant,
    can_manage_tenant_learning,
    can_mutate_tenant_data,
    can_read_tenant_data,
    can_read_platform,
    can_reactivate_tenant,
    is_platform_user,
    is_platform_admin,
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
def platform_tenant_create(request):
    if not can_manage_platform(request.user):
        return HttpResponseForbidden('Only platform admins can create organizations.')
    if request.method == 'POST':
        form = TenantSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tenant-list')
    else:
        form = TenantSignupForm()
    return render(request, 'core/platform_tenant_create.html', {'form': form})


@login_required
@never_cache
def platform_account_create(request):
    if not can_reactivate_tenant(request.user):
        return HttpResponseForbidden('Only Super Admin can provision platform accounts.')
    created_account = None
    if request.method == 'POST':
        form = PlatformAccountProvisionForm(request.POST)
        if form.is_valid():
            temporary_password = secrets.token_urlsafe(18)
            account = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                role=form.cleaned_data['role'],
                tenant=None,
                password=temporary_password,
                must_change_password=True,
            )
            created_account = {'user': account, 'password': temporary_password}
    else:
        form = PlatformAccountProvisionForm()
    return render(
        request,
        'core/platform_account_create.html',
        {'form': form, 'created_account': created_account},
    )


def tenant_selected_for_user(user, tenant_id=None):
    if tenant_id is not None:
        if not is_platform_admin(user):
            return None
        tenant = get_object_or_404(Tenant, id=tenant_id)
    elif is_tenant_admin(user) and user.tenant_id:
        tenant = user.tenant
    else:
        return None
    return tenant if can_manage_tenant(user, tenant) else None


@login_required
def tenant_user_list(request, tenant_id=None):
    tenant = tenant_selected_for_user(request.user, tenant_id)
    if tenant is None:
        return HttpResponseForbidden('You cannot view learners for this organization.')
    learners = User.objects.filter(tenant=tenant, role=User.Role.TENANT_USER).order_by('username')
    return render(
        request,
        'core/tenant_user_list.html',
        {
            'tenant': tenant,
            'learners': learners,
            'can_edit_users': can_mutate_tenant_data(request.user, tenant),
        },
    )


@login_required
def tenant_user_update(request, user_id, tenant_id=None):
    tenant = tenant_selected_for_user(request.user, tenant_id)
    if tenant is None:
        return HttpResponseForbidden('You cannot manage learners for this organization.')
    if not can_mutate_tenant_data(request.user, tenant):
        return HttpResponseForbidden('This tenant is read-only.')
    learner = get_object_or_404(
        User, id=user_id, tenant=tenant, role=User.Role.TENANT_USER
    )
    if request.method == 'POST':
        form = TenantUserManagementForm(request.POST, instance=learner)
        if form.is_valid():
            form.save()
            if tenant_id:
                return redirect('platform-tenant-users', tenant_id=tenant.id)
            return redirect('tenant-user-list')
    else:
        form = TenantUserManagementForm(instance=learner)
    return render(
        request,
        'core/tenant_user_form.html',
        {'tenant': tenant, 'learner': learner, 'form': form},
    )


class RequiredPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        return response

@login_required
def dashboard(request):
    user = request.user
    context = {
        'can_manage_platform': can_manage_platform(user),
        'can_read_platform': can_read_platform(user),
        'can_reactivate_tenant': can_reactivate_tenant(user),
        'tenant_count': None,
        'tenant_user_count': None,
        'onboarding_steps': [],
        'assigned_course': None,
        'assigned_course_count': 0,
        'assigned_lesson': None,
    }

    if user.role in {User.Role.SUPER_ADMIN, User.Role.ADMIN, User.Role.SUPER_VIEWER}:
        context['tenant_count'] = Tenant.objects.count()
    elif user.tenant_id:
        context['tenant_user_count'] = User.objects.filter(tenant=user.tenant).count()
        if is_tenant_admin(user) and can_mutate_tenant_data(user):
            tenant_courses = Course.objects.filter(tenant=user.tenant).order_by('created_at', 'id')
            first_course = tenant_courses.first()
            learner_count = User.objects.filter(
                tenant=user.tenant,
                role=User.Role.TENANT_USER,
            ).count()
            has_lessons = Lesson.objects.filter(course__tenant=user.tenant).exists()
            onboarding_steps = []

            # Tenant signup requires an organization name, so valid tenants have
            # already completed the naming step and do not see it repeatedly.
            if not user.tenant.name.strip():
                onboarding_steps.append(
                    {
                        'label': 'Name your institute',
                        'url': reverse('organization-settings'),
                        'action': 'Review settings',
                    }
                )
            if first_course is None:
                onboarding_steps.append(
                    {
                        'label': 'Create your first course',
                        'url': reverse('course-create'),
                        'action': 'Create course',
                    }
                )
            if not has_lessons and first_course:
                course_without_lessons = next(
                    (course for course in tenant_courses if not course.lessons.exists()),
                    first_course,
                )
                onboarding_steps.append(
                    {
                        'label': 'Add your first lesson',
                        'url': reverse('lesson-create', args=[course_without_lessons.id]),
                        'action': 'Add lesson',
                    }
                )
            if learner_count == 0:
                onboarding_steps.append(
                    {
                        'label': 'Onboard your first learner',
                        'url': reverse('bulk-student-add'),
                        'action': 'Enroll students',
                    }
                )
            context['onboarding_steps'] = onboarding_steps
        elif is_tenant_user(user):
            assigned_courses = visible_courses_for_user(user)
            context['assigned_course_count'] = assigned_courses.count()
            context['assigned_course'] = assigned_courses.order_by('title').first()
            if context['assigned_course']:
                context['assigned_lesson'] = context['assigned_course'].lessons.order_by('order', 'id').first()

    return render(request, 'core/dashboard.html', context)


def save_lesson_uploads(lesson, uploads, remove_video=False):
    if not uploads and not remove_video:
        return

    created_assets = []
    try:
        if remove_video:
            for asset in lesson.assets.filter(kind=LessonAsset.Kind.VIDEO):
                lesson.content = lesson.content.replace(asset.markdown_embed(), '').strip()
                asset.delete()

        embeds = []
        for upload in uploads:
            kind, mime_type = classify_lesson_upload(upload)
            asset = LessonAsset(lesson=lesson, kind=kind, mime_type=mime_type)
            asset.file.save(upload.name, upload, save=False)
            created_assets.append(asset)
            asset.full_clean()
            asset.save()
            embeds.append(asset.markdown_embed())

        if embeds:
            markdown = '\n\n'.join(embeds)
            lesson.content = f'{lesson.content.rstrip()}\n\n{markdown}' if lesson.content.strip() else markdown
        lesson.save(update_fields=['content'])
    except Exception:
        for asset in created_assets:
            if asset.file:
                asset.file.storage.delete(asset.file.name)
        raise


@login_required
def course_assistant_preview(request):
    if not is_tenant_admin(request.user):
        return HttpResponseForbidden('Only tenant admins can view the course assistant preview.')

    preview = None
    if request.method == 'POST':
        form = CourseAssistantPreviewForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            duration = data['duration_weeks']
            module_titles = [
                'Foundations and baseline',
                'Core concepts',
                'Guided practice',
                'Applied project and review',
            ][:min(duration, 4)]
            module_count = len(module_titles)
            modules = []
            for index, title in enumerate(module_titles):
                start_week = (index * duration) // module_count + 1
                end_week = ((index + 1) * duration) // module_count
                modules.append(
                    {
                        'title': title,
                        'start_week': start_week,
                        'end_week': end_week,
                        'estimated_hours': data['hours_per_week'] * (end_week - start_week + 1),
                    }
                )
            preview = {
                'inputs': data,
                'current_level_label': dict(form.fields['current_level'].choices)[data['current_level']],
                'modules': modules,
            }
    else:
        form = CourseAssistantPreviewForm()

    return render(request, 'core/course_assistant_preview.html', {'form': form, 'preview': preview})


@login_required
def course_list(request, tenant_id=None):
    user = request.user
    visible_courses = visible_courses_for_user(user)
    tenant_filter = None
    selected_tenant_id = tenant_id or (
        request.GET.get('tenant_id') if is_platform_user(user) else None
    )
    if tenant_id is not None and not is_platform_user(user):
        return HttpResponseForbidden('Only platform users can select an organization.')
    if selected_tenant_id:
        tenant_filter = get_object_or_404(Tenant, id=selected_tenant_id)
        visible_courses = visible_courses.filter(tenant=tenant_filter)
    manageable_course_ids = [
        course.id
        for course in visible_courses
        if can_manage_tenant_learning(user, course.tenant)
    ]
    if tenant_filter is not None:
        can_create_courses = can_manage_tenant_learning(user, tenant_filter)
    else:
        can_create_courses = bool(
            is_tenant_admin(user) and can_mutate_tenant_data(user)
            or is_platform_admin(user)
            and Tenant.objects.filter(
                status=Tenant.Status.ACTIVE,
                trial_ends_at__gt=timezone.now(),
            ).exists()
        )

    return render(
        request,
        'core/course_list.html',
        {
            'courses': visible_courses,
            'can_create_courses': can_create_courses,
            'manageable_course_ids': manageable_course_ids,
            'tenant_filter': tenant_filter,
        },
    )


@login_required
def tenant_list(request):
    if not is_platform_user(request.user):
        return HttpResponseForbidden('Only platform users can view tenants.')
    tenants = Tenant.objects.all()
    mutable_tenant_ids = [
        tenant.id for tenant in tenants if can_mutate_tenant_data(request.user, tenant)
    ]
    return render(
        request,
        'core/tenant_list.html',
        {
            'tenants': tenants,
            'can_reactivate_tenants': can_reactivate_tenant(request.user),
            'can_create_tenants': can_manage_platform(request.user),
            'can_manage_tenant_content': is_platform_admin(request.user),
            'mutable_tenant_ids': mutable_tenant_ids,
        },
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
def tenant_subscription_settings(request, tenant_id):
    if not can_reactivate_tenant(request.user):
        return HttpResponseForbidden('Only Super Admin can change subscription or expiration settings.')
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if request.method == 'POST':
        form = TenantSubscriptionForm(request.POST, tenant=tenant)
        if form.is_valid():
            tenant.subscription_status = form.cleaned_data['subscription_status']
            if tenant.subscription_status == Tenant.SubscriptionStatus.SUBSCRIBED:
                tenant.status = Tenant.Status.ACTIVE
                tenant.expired_at = None
            else:
                tenant.trial_ends_at = form.cleaned_data['resolved_trial_ends_at']
                if tenant.is_trial_expired():
                    tenant.status = Tenant.Status.EXPIRED
                    tenant.expired_at = timezone.now()
                else:
                    tenant.status = Tenant.Status.ACTIVE
                    tenant.expired_at = None
            tenant.save()
            return redirect('tenant-list')
    else:
        form = TenantSubscriptionForm(tenant=tenant)
    return render(request, 'core/tenant_subscription_settings.html', {'tenant': tenant, 'form': form})


@login_required
@never_cache
def tenant_logo(request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not tenant.logo or not can_read_tenant_data(request.user, tenant):
        raise Http404
    mime_type = image_mime_type(tenant.logo.name)
    if not mime_type:
        raise Http404
    try:
        file_handle = tenant.logo.open('rb')
    except (OSError, ValueError):
        raise Http404
    response = FileResponse(file_handle, content_type=mime_type)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@never_cache
def user_avatar(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    may_view = (
        request.user.id == profile_user.id
        or is_platform_user(request.user)
        or is_tenant_admin(request.user)
        and request.user.tenant_id == profile_user.tenant_id
    )
    if not profile_user.avatar or not may_view:
        raise Http404
    mime_type = image_mime_type(profile_user.avatar.name)
    if not mime_type:
        raise Http404
    try:
        file_handle = profile_user.avatar.open('rb')
    except (OSError, ValueError):
        raise Http404
    response = FileResponse(file_handle, content_type=mime_type)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
def organization_settings(request, tenant_id=None):
    user = request.user
    if tenant_id is not None:
        if not is_platform_admin(user):
            return HttpResponseForbidden('Only platform admins can select an organization.')
        tenant = get_object_or_404(Tenant, id=tenant_id)
    elif is_tenant_admin(user) and user.tenant_id:
        tenant = user.tenant
    else:
        return HttpResponseForbidden('Only tenant admins can manage organization settings.')
    if not can_manage_tenant(user, tenant):
        return HttpResponseForbidden('You cannot manage this organization.')
    if not can_mutate_tenant_data(user, tenant):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = TenantSettingsForm(request.POST, request.FILES, instance=tenant)
        if form.is_valid():
            form.save()
            return redirect('tenant-list' if tenant_id else 'dashboard')
    else:
        form = TenantSettingsForm(instance=tenant)
    return render(request, 'core/organization_settings.html', {'form': form})


@login_required
def profile_settings(request):
    user = request.user
    if user.role in User.TENANT_ROLES and not can_mutate_tenant_data(user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = ProfileSettingsForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)
            if (
                form.cleaned_data.get('remove_avatar')
                and not isinstance(form.cleaned_data.get('avatar'), UploadedFile)
            ):
                updated_user.avatar = ''
            updated_user.save()
            return redirect('dashboard')
    else:
        form = ProfileSettingsForm(instance=user)
    return render(request, 'core/profile_settings.html', {'form': form})


@login_required
@never_cache
def bulk_student_add(request, tenant_id=None):
    user = request.user
    if tenant_id is not None:
        if not is_platform_admin(user):
            return HttpResponseForbidden('Only platform admins can select an organization.')
        tenant = get_object_or_404(Tenant, id=tenant_id)
    elif is_tenant_admin(user) and user.tenant_id:
        tenant = user.tenant
    else:
        return HttpResponseForbidden('Only tenant admins can onboard students.')
    if not can_manage_tenant(user, tenant):
        return HttpResponseForbidden('You cannot onboard learners for this organization.')
    if not can_mutate_tenant_data(user, tenant):
        return HttpResponseForbidden('This tenant is read-only.')

    created_students = []
    csv_form = StudentCsvImportForm()
    csv_result = None
    if request.method == 'POST' and request.POST.get('action') == 'import_csv':
        csv_form = StudentCsvImportForm(request.POST, request.FILES)
        if csv_form.is_valid():
            csv_result = import_student_csv(csv_form.cleaned_data['csv_file'], tenant)
        form = BulkStudentOnboardingForm(tenant=tenant)
    elif request.method == 'POST':
        form = BulkStudentOnboardingForm(request.POST, tenant=tenant)
        if form.is_valid():
            with transaction.atomic():
                for student_data in form.cleaned_data['students']:
                    initial_password = secrets.token_urlsafe(12)
                    student = User.objects.create_user(
                        username=student_data['username'],
                        email=student_data['email'],
                        password=initial_password,
                        role=User.Role.TENANT_USER,
                        must_change_password=True,
                        tenant=tenant,
                    )
                    created_students.append(
                        {'username': student.username, 'email': student.email, 'password': initial_password}
                    )
    else:
        form = BulkStudentOnboardingForm(tenant=tenant)

    return render(
        request,
        'core/bulk_student_add.html',
        {
            'form': form,
            'created_students': created_students,
            'csv_form': csv_form,
            'csv_result': csv_result,
            'tenant': tenant,
        },
    )


@login_required
@never_cache
def download_student_csv_template(request, tenant_id=None):
    user = request.user
    if tenant_id is not None:
        if not is_platform_admin(user):
            return HttpResponseForbidden('Only platform admins can select an organization.')
        tenant = get_object_or_404(Tenant, id=tenant_id)
    elif is_tenant_admin(user) and user.tenant_id:
        tenant = user.tenant
    else:
        return HttpResponseForbidden('Only tenant admins can download the enrollment template.')
    if not can_manage_tenant(user, tenant):
        return HttpResponseForbidden('You cannot onboard learners for this organization.')
    if not can_mutate_tenant_data(user, tenant):
        return HttpResponseForbidden('This tenant is read-only.')

    response = HttpResponse(blank_enrollment_csv(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="learnant-students-template.csv"'
    return response


@login_required
def course_create(request):
    user = request.user
    platform_manager = is_platform_admin(user)
    if not platform_manager and not is_tenant_admin(user):
        return HttpResponseForbidden('Only tenant admins and platform admins can create courses.')
    if not platform_manager and not can_mutate_tenant_data(user):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = CourseForm(request.POST, platform_tenant_management=platform_manager)
        if form.is_valid():
            course = form.save(commit=False)
            course.tenant = form.cleaned_data['tenant'] if platform_manager else user.tenant
            course.creator = user
            if not can_mutate_tenant_data(user, course.tenant):
                return HttpResponseForbidden('This tenant is read-only.')
            course.save()
            return redirect('course-list')
    else:
        form = CourseForm(platform_tenant_management=platform_manager)
        selected_tenant_id = request.GET.get('tenant_id') if platform_manager else None
        if selected_tenant_id:
            if form.fields['tenant'].queryset.filter(id=selected_tenant_id).exists():
                form.fields['tenant'].initial = selected_tenant_id

    return render(request, 'core/course_form.html', {'form': form})


@login_required
def course_update(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot manage this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
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
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot manage this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
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
            'can_manage_course': can_manage_tenant(request.user, course.tenant),
            'can_create_lessons': can_manage_tenant_learning(request.user, course.tenant),
            'can_update_progress': bool(assignment and can_mutate_tenant_data(request.user)),
        },
    )


@login_required
def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    lessons = list(Lesson.objects.filter(course=course).order_by('order', 'id'))
    lesson_index = next(index for index, row in enumerate(lessons) if row.id == lesson.id)

    assignment = None
    progress = None
    if is_tenant_user(request.user):
        assignment = get_object_or_404(CourseAssignment, course=course, learner=request.user)
        progress = LessonProgress.objects.filter(assignment=assignment, lesson=lesson).first()

    return render(
        request,
        'core/lesson_detail.html',
        {
            'course': course,
            'lesson': lesson,
            'previous_lesson': lessons[lesson_index - 1] if lesson_index > 0 else None,
            'next_lesson': lessons[lesson_index + 1] if lesson_index + 1 < len(lessons) else None,
            'syllabus': lessons,
            'assignment': assignment,
            'progress': progress,
            'can_update_progress': bool(assignment and can_mutate_tenant_data(request.user)),
            'can_manage_lesson': can_manage_tenant(request.user, course.tenant),
            'video_player': lesson.video_player,
        },
    )


@login_required
def lesson_create(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot manage lessons for this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            with transaction.atomic():
                lesson.save()
                save_lesson_uploads(
                    lesson,
                    form.cleaned_data['media_files'],
                    form.cleaned_data['remove_video'],
                )
            return redirect('lesson-list', course_id=course.id)
    else:
        next_order = (
            Lesson.objects.filter(course=course).aggregate(max_order=Max('order'))['max_order'] or 0
        ) + 1
        form = LessonForm(initial={'order': next_order})

    return render(
        request,
        'core/lesson_form.html',
        {'course': course, 'form': form, 'has_uploaded_video': False},
    )


@login_required
@never_cache
def lesson_asset(request, asset_id):
    asset = get_object_or_404(
        LessonAsset.objects.select_related('lesson__course'),
        public_id=asset_id,
    )
    if not visible_courses_for_user(request.user).filter(id=asset.lesson.course_id).exists():
        raise Http404
    try:
        file_handle = asset.file.open('rb')
    except (OSError, ValueError):
        raise Http404
    response = FileResponse(file_handle, content_type=asset.mime_type)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
def lesson_update(request, course_id, lesson_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot manage lessons for this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            updated_lesson = form.save(commit=False)
            updated_lesson.course = course
            with transaction.atomic():
                updated_lesson.save()
                save_lesson_uploads(
                    updated_lesson,
                    form.cleaned_data['media_files'],
                    form.cleaned_data['remove_video'],
                )
            return redirect('lesson-list', course_id=course.id)
    else:
        form = LessonForm(instance=lesson)

    return render(
        request,
        'core/lesson_form.html',
        {
            'course': course,
            'lesson': lesson,
            'form': form,
            'has_uploaded_video': lesson.assets.filter(kind=LessonAsset.Kind.VIDEO).exists(),
        },
    )


@login_required
def lesson_reorder(request, course_id):
    if request.method != 'POST':
        return HttpResponseForbidden('Lesson reordering must use POST.')
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot reorder lessons for this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
        return HttpResponseForbidden('This tenant is read-only.')

    try:
        lesson_id = int(request.POST.get('lesson_id', ''))
    except (TypeError, ValueError):
        return HttpResponseForbidden('Invalid lesson selection.')
    direction = request.POST.get('direction')
    if direction not in {'up', 'down'}:
        return HttpResponseForbidden('Invalid reorder direction.')

    with transaction.atomic():
        Course.objects.select_for_update().get(pk=course.pk)
        lessons = list(
            Lesson.objects.select_for_update().filter(course=course).order_by('order', 'id')
        )
        current_index = next(
            (index for index, lesson in enumerate(lessons) if lesson.id == lesson_id),
            None,
        )
        if current_index is None:
            return HttpResponseForbidden('Lesson does not belong to this course.')

        target_index = current_index - 1 if direction == 'up' else current_index + 1
        if 0 <= target_index < len(lessons):
            lessons[current_index], lessons[target_index] = lessons[target_index], lessons[current_index]
            max_order = max(lesson.order for lesson in lessons)

            # Move every row into unique temporary buffer positions first. This
            # avoids transient collisions with the immediate unique constraint
            # while assigning the final contiguous 1..N positions.
            buffer_start = max_order + len(lessons) + 1
            for index, lesson in enumerate(lessons):
                Lesson.objects.filter(pk=lesson.pk).update(order=buffer_start + index)
            for index, lesson in enumerate(lessons, start=1):
                Lesson.objects.filter(pk=lesson.pk).update(order=index)

    return redirect('lesson-list', course_id=course.id)


@login_required
def lesson_delete(request, course_id, lesson_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot manage lessons for this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
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
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot manage assignments for this tenant course.')
    assignments = CourseAssignment.objects.select_related('learner').filter(course=course)
    return render(
        request,
        'core/assignment_list.html',
        {
            'course': course,
            'assignments': assignments,
            'can_create_assignments': can_manage_tenant_learning(request.user, course.tenant),
        },
    )


@login_required
def assignment_create(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot assign learners to this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
        return HttpResponseForbidden('This tenant is read-only.')

    if request.method == 'POST':
        form = CourseAssignmentForm(request.POST, tenant=course.tenant)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.tenant = course.tenant
            assignment.course = course
            assignment.save()
            return redirect('assignment-list', course_id=course.id)
    else:
        form = CourseAssignmentForm(tenant=course.tenant)

    return render(request, 'core/assignment_form.html', {'course': course, 'form': form})


@login_required
def assignment_delete(request, course_id, assignment_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot revoke assignments for this tenant course.')
    if not can_mutate_tenant_data(request.user, course.tenant):
        return HttpResponseForbidden('This tenant is read-only.')
    assignment = get_object_or_404(CourseAssignment, id=assignment_id, course=course, tenant=course.tenant)
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
    return redirect('lesson-detail', course_id=course.id, lesson_id=lesson.id)


@login_required
def progress_list(request, course_id):
    course = get_object_or_404(visible_courses_for_user(request.user), id=course_id)
    if not can_manage_tenant(request.user, course.tenant):
        return HttpResponseForbidden('You cannot view progress for this tenant course.')
    assignments = CourseAssignment.objects.select_related('learner').filter(course=course)
    progress_records = LessonProgress.objects.select_related('assignment__learner', 'lesson').filter(
        assignment__course=course
    )
    return render(
        request,
        'core/progress_list.html',
        {'course': course, 'assignments': assignments, 'progress_records': progress_records},
    )
