from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Course, Tenant, User


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
