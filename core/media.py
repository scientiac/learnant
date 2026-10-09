from pathlib import PurePath

from django.core.exceptions import ValidationError


LESSON_UPLOAD_TYPES = {
    '.png': ('image', 'image/png'),
    '.jpg': ('image', 'image/jpeg'),
    '.jpeg': ('image', 'image/jpeg'),
    '.gif': ('image', 'image/gif'),
    '.webp': ('image', 'image/webp'),
    '.mp4': ('video', 'video/mp4'),
    '.webm': ('video', 'video/webm'),
    '.ogg': ('video', 'video/ogg'),
}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 100 * 1024 * 1024


def classify_lesson_upload(upload):
    extension = PurePath(upload.name).suffix.lower()
    media_type = LESSON_UPLOAD_TYPES.get(extension)
    if media_type is None:
        raise ValidationError('Upload PNG, JPEG, GIF, WebP, MP4, WebM, or Ogg files only.')
    kind, mime_type = media_type
    max_size = MAX_VIDEO_SIZE if kind == 'video' else MAX_IMAGE_SIZE
    if upload.size > max_size:
        limit_mb = max_size // (1024 * 1024)
        raise ValidationError(f'{upload.name} exceeds the {limit_mb} MB limit.')
    return kind, mime_type
