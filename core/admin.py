from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Course, CourseAssignment, Lesson, LessonProgress, Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'trial_starts_at', 'trial_ends_at')
    list_filter = ('status',)
    search_fields = ('name',)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Tenant role', {'fields': ('role', 'tenant')}),
    )
    list_display = ('username', 'email', 'role', 'tenant', 'is_staff', 'is_active')
    list_filter = UserAdmin.list_filter + ('role',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'creator', 'created_at')
    list_filter = ('tenant',)
    search_fields = ('title', 'description', 'tenant__name')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'created_at')
    list_filter = ('course__tenant', 'course')
    search_fields = ('title', 'content', 'course__title')
    fields = ('course', 'title', 'description', 'content', 'order')


@admin.register(CourseAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('course', 'learner', 'tenant', 'assigned_at')
    list_filter = ('tenant',)
    search_fields = ('course__title', 'learner__username', 'tenant__name')


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'learner_username', 'is_complete', 'completed_at')
    list_filter = ('is_complete', 'assignment__tenant')
    search_fields = ('lesson__title', 'assignment__learner__username')

    def learner_username(self, obj):
        return obj.assignment.learner.username
