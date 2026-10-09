from django.core.management.base import BaseCommand

from core.models import Course, CourseAssignment, Lesson, Tenant, User


class Command(BaseCommand):
    help = 'Create idempotent local demo tenants and users.'

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(name='Demo Institute')
        users = [
            ('superadmin', User.Role.SUPER_ADMIN, None),
            ('admin', User.Role.ADMIN, None),
            ('viewer', User.Role.SUPER_VIEWER, None),
            ('tenant_admin', User.Role.TENANT_ADMIN, tenant),
            ('institute_admin', User.Role.TENANT_ADMIN, tenant),
            ('learner', User.Role.TENANT_USER, tenant),
        ]

        for username, role, user_tenant in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'role': role, 'tenant': user_tenant, 'password': 'initial-demo-password'},
            )
            if not created:
                user.role = role
                user.tenant = user_tenant
            user.set_password('password123')
            user.save()

        tenant_admin = User.objects.get(username='tenant_admin')
        course, _ = Course.objects.get_or_create(
            tenant=tenant,
            title='Getting Started',
            defaults={
                'description': 'A sample course for the demo institute.',
                'creator': tenant_admin,
            },
        )
        Lesson.objects.get_or_create(
            course=course,
            order=1,
            defaults={
                'title': 'Welcome',
                'content': 'This is the first demo lesson.',
            },
        )
        learner = User.objects.get(username='learner')
        CourseAssignment.objects.get_or_create(tenant=tenant, course=course, learner=learner)

        self.stdout.write(self.style.SUCCESS('Demo data ready. Password for all demo users: password123'))
