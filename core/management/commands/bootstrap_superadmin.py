import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as PasswordValidationError
from django.core.management.base import BaseCommand, CommandError

from core.models import User


class Command(BaseCommand):
    help = 'Provision the first platform Super Admin from deployment environment variables.'

    ENVIRONMENT_KEYS = (
        'LEARNANT_SUPERADMIN_USERNAME',
        'LEARNANT_SUPERADMIN_EMAIL',
        'LEARNANT_SUPERADMIN_PASSWORD',
    )

    def handle(self, *args, **options):
        missing = [key for key in self.ENVIRONMENT_KEYS if not os.environ.get(key)]
        if missing:
            raise CommandError(f'Missing required environment variables: {", ".join(missing)}')

        username = os.environ['LEARNANT_SUPERADMIN_USERNAME'].strip()
        email = os.environ['LEARNANT_SUPERADMIN_EMAIL'].strip()
        password = os.environ['LEARNANT_SUPERADMIN_PASSWORD']
        if not username or not email:
            raise CommandError('Super Admin username and email must not be blank.')

        existing = User.objects.filter(username__iexact=username).first()
        if existing:
            if existing.role != User.Role.SUPER_ADMIN or existing.tenant_id is not None or not existing.is_superuser:
                raise CommandError('That username already belongs to a non-bootstrap account.')
            self.stdout.write(self.style.SUCCESS('Bootstrap Super Admin already exists; no changes made.'))
            return

        try:
            validate_password(password)
        except PasswordValidationError as error:
            raise CommandError('; '.join(error.messages)) from error

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=User.Role.SUPER_ADMIN,
            tenant=None,
            is_staff=True,
            is_superuser=True,
            must_change_password=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Provisioned bootstrap Super Admin: {username}'))
