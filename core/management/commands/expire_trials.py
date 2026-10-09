from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Tenant


class Command(BaseCommand):
    help = 'Mark active tenants with ended trials as expired. Safe to run repeatedly.'

    def handle(self, *args, **options):
        now = timezone.now()
        tenants = Tenant.objects.filter(
            status=Tenant.Status.ACTIVE,
            subscription_status=Tenant.SubscriptionStatus.TRIAL,
            trial_ends_at__lte=now,
        )
        count = 0
        for tenant in tenants:
            tenant.mark_expired(now)
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Expired {count} tenant(s).'))
