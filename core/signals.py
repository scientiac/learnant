from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import LessonAsset, Tenant, User


@receiver(post_delete, sender=LessonAsset)
def remove_deleted_lesson_asset_file(sender, instance, **kwargs):
    if instance.file:
        storage = instance.file.storage
        name = instance.file.name
        transaction.on_commit(lambda: storage.delete(name))


@receiver(pre_save, sender=Tenant)
def remove_replaced_tenant_logo(sender, instance, **kwargs):
    if not instance.pk:
        return
    old_name = sender.objects.filter(pk=instance.pk).values_list('logo', flat=True).first()
    new_name = instance.logo.name if instance.logo else ''
    if old_name and old_name != new_name:
        storage = instance.logo.storage
        transaction.on_commit(lambda: storage.delete(old_name))


@receiver(post_delete, sender=Tenant)
def remove_deleted_tenant_logo(sender, instance, **kwargs):
    if instance.logo:
        storage = instance.logo.storage
        name = instance.logo.name
        transaction.on_commit(lambda: storage.delete(name))


@receiver(pre_save, sender=User)
def remove_replaced_user_avatar(sender, instance, **kwargs):
    if not instance.pk:
        return
    old_name = sender.objects.filter(pk=instance.pk).values_list('avatar', flat=True).first()
    new_name = instance.avatar.name if instance.avatar else ''
    if old_name and old_name != new_name:
        storage = instance.avatar.storage
        transaction.on_commit(lambda: storage.delete(old_name))


@receiver(post_delete, sender=User)
def remove_deleted_user_avatar(sender, instance, **kwargs):
    if instance.avatar:
        storage = instance.avatar.storage
        name = instance.avatar.name
        transaction.on_commit(lambda: storage.delete(name))
