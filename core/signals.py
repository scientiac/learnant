from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import LessonAsset


@receiver(post_delete, sender=LessonAsset)
def remove_deleted_lesson_asset_file(sender, instance, **kwargs):
    if instance.file:
        storage = instance.file.storage
        name = instance.file.name
        transaction.on_commit(lambda: storage.delete(name))
