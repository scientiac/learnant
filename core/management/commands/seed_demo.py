from django.core.management.base import BaseCommand

from core.models import Tenant, User


class Command(BaseCommand):
    help = 'Create idempotent local demo tenants and users.'

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(name='Demo Institute')
        users = [
            ('superadmin', User.Role.SUPER_ADMIN, None),
            ('admin', User.Role.ADMIN, None),
            ('viewer', User.Role.SUPER_VIEWER, None),
            ('tenantadmin', User.Role.TENANT_ADMIN, tenant),
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

        self.stdout.write(self.style.SUCCESS('Demo data ready. Password for all demo users: password123'))
