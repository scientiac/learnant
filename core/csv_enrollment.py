import csv
import io
import secrets

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils.text import slugify

from .models import Course, CourseAssignment, Tenant, User


CSV_HEADERS = ('username', 'email', 'first_name', 'last_name', 'course_ids')
REQUIRED_HEADERS = set(CSV_HEADERS[:4])
MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_CSV_ROWS = 500


def blank_enrollment_csv(tenant):
    output = io.StringIO(newline='')
    tenant_name = tenant.name.replace('\r', ' ').replace('\n', ' ').replace(',', ' ')
    output.write(f'# Learnant learner roster template for {tenant_name}\n')
    output.write('# Course IDs for this organization (separate multiple IDs with semicolons):\n')
    for course in Course.objects.filter(tenant=tenant).order_by('id'):
        course_title = course.title.replace('\r', ' ').replace('\n', ' ').replace(',', ' ')
        output.write(f'# {course.id}: {course_title}\n')
    output.write('\n')
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    return output.getvalue()


def username_from_email(email, reserved_usernames=()):
    base = (slugify(email.split('@', 1)[0]) or 'learner')[:140]
    username = base
    suffix = 1
    reserved = {value.casefold() for value in reserved_usernames}
    while username.casefold() in reserved or User.objects.filter(username__iexact=username).exists():
        suffix += 1
        username = f'{base[:140 - len(str(suffix))]}{suffix}'
    return username


def create_learner(tenant, *, username, email, first_name, last_name, courses=()):
    """Create one forced-reset learner and any selected same-tenant assignments."""
    with transaction.atomic():
        password = secrets.token_urlsafe(18)
        learner = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role=User.Role.TENANT_USER,
            tenant=tenant,
            must_change_password=True,
        )
        for course in courses:
            CourseAssignment.objects.get_or_create(
                tenant=tenant,
                course=course,
                learner=learner,
            )
    return {'username': username, 'email': email, 'password': password, 'course_count': len(courses)}


def import_student_csv(upload, tenant):
    """Import valid rows independently; every account is bound to ``tenant``."""
    result = {'created_students': [], 'row_errors': [], 'skipped_count': 0, 'file_error': ''}
    if upload.size > MAX_CSV_BYTES:
        result['file_error'] = 'CSV files must be 5 MB or smaller.'
        return result
    try:
        text = upload.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        result['file_error'] = 'CSV must use UTF-8 encoding.'
        return result

    try:
        csv_text = '\n'.join(
            line for line in text.splitlines()
            if not line.lstrip().startswith('#')
        ).lstrip('\r\n')
        reader = csv.DictReader(io.StringIO(csv_text, newline=''))
        headers = reader.fieldnames or []
        normalized_headers = [header.strip().lower() for header in headers]
        if len(set(normalized_headers)) != len(normalized_headers):
            result['file_error'] = 'CSV contains duplicate column headers.'
            return result
        missing = REQUIRED_HEADERS - set(normalized_headers)
        unknown = set(normalized_headers) - set(CSV_HEADERS)
        if missing or unknown:
            messages = []
            if missing:
                messages.append(f'Missing columns: {", ".join(sorted(missing))}.')
            if unknown:
                messages.append(f'Unknown columns: {", ".join(sorted(unknown))}.')
            result['file_error'] = ' '.join(messages)
            return result
        rows = []
        for row_number, raw_row in enumerate(reader, start=2):
            if row_number > MAX_CSV_ROWS + 1:
                result['file_error'] = f'CSV may contain at most {MAX_CSV_ROWS} learner rows.'
                return result
            row = {
                (key or '').strip().lower(): (value or '').strip()
                for key, value in raw_row.items()
                if key is not None
            }
            if not any(row.values()) and raw_row.get(None) is None:
                continue
            rows.append((row_number, row, raw_row.get(None)))
    except csv.Error:
        result['file_error'] = 'CSV formatting is invalid.'
        return result

    courses_by_id = {str(course.id): course for course in Course.objects.filter(tenant=tenant)}

    seen_usernames = set()
    seen_emails = set()
    for row_number, row, extra_values in rows:
        errors = []
        if extra_values:
            errors.append('row has more values than headers')
        username = row.get('username', '')
        email = row.get('email', '')
        first_name = row.get('first_name', '')
        last_name = row.get('last_name', '')

        if len(first_name) > 150 or len(last_name) > 150:
            errors.append('first_name and last_name must be 150 characters or fewer')
        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.append(f'invalid email "{email}"')
            if email.casefold() in seen_emails or User.objects.filter(email__iexact=email).exists():
                errors.append(f'email "{email}" is already in use')
        if not username and email:
            base = (slugify(email.split('@', 1)[0]) or 'learner')[:140]
            username = base
            suffix = 1
            while username.casefold() in seen_usernames or User.objects.filter(username__iexact=username).exists():
                suffix += 1
                username = f'{base[:140 - len(str(suffix))]}{suffix}'
        elif not username and not email:
            errors.append('username or email is required')

        if username:
            if len(username) > 150:
                errors.append('username must be 150 characters or fewer')
            else:
                try:
                    User._meta.get_field('username').run_validators(username)
                except ValidationError:
                    errors.append(f'invalid username "{username}"')
                if username.casefold() in seen_usernames or User.objects.filter(username__iexact=username).exists():
                    errors.append(f'username "{username}" is already in use')

        course_rows = []
        course_ids_text = row.get('course_ids', '')
        if course_ids_text:
            for course_id in dict.fromkeys(part.strip() for part in course_ids_text.split(';') if part.strip()):
                course = courses_by_id.get(course_id)
                if course is None:
                    errors.append(f'course ID "{course_id}" is not in this organization')
                else:
                    course_rows.append(course)

        if errors:
            result['row_errors'].append({'row': row_number, 'errors': errors})
            result['skipped_count'] += 1
            continue

        try:
            created_student = create_learner(
                tenant,
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                courses=course_rows,
            )
        except IntegrityError:
            result['row_errors'].append(
                {'row': row_number, 'errors': ['account conflicts with an account created concurrently']}
            )
            result['skipped_count'] += 1
            continue

        seen_usernames.add(username.casefold())
        if email:
            seen_emails.add(email.casefold())
        result['created_students'].append(created_student)

    return result
