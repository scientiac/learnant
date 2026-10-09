import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def settings_environment(**values):
    env = os.environ.copy()
    for key in (
        'DEBUG', 'DJANGO_DEBUG', 'SECRET_KEY', 'DJANGO_SECRET_KEY', 'ALLOWED_HOSTS',
        'DJANGO_ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', 'DATABASE_URL', 'POSTGRES_DB',
        'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT',
        'RAILWAY_PUBLIC_DOMAIN',
    ):
        env.pop(key, None)
    env.update(values)
    return env


class DeploymentSettingsTests(SimpleTestCase):
    def run_settings_probe(self, code, **values):
        return subprocess.run(
            [sys.executable, '-c', code],
            cwd=PROJECT_ROOT,
            env=settings_environment(**values),
            capture_output=True,
            text=True,
        )

    def test_production_environment_configures_postgres_hosts_csrf_and_whitenoise(self):
        result = self.run_settings_probe(
            """
from config import settings
assert settings.DEBUG is False
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
assert settings.ALLOWED_HOSTS == ['learnant.example.org', 'learnant.example.net']
assert settings.CSRF_TRUSTED_ORIGINS == ['https://learnant.example.org']
assert 'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE
assert settings.STORAGES['staticfiles']['BACKEND'] == 'whitenoise.storage.CompressedManifestStaticFilesStorage'
assert settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
assert settings.SECURE_SSL_REDIRECT and settings.SECURE_HSTS_SECONDS > 0
assert settings.MAILERS['default']['BACKEND'] == 'django.core.mail.backends.smtp.EmailBackend'
""",
            DEBUG='false',
            SECRET_KEY='a-secure-test-key-that-is-not-used-for-any-real-data',
            ALLOWED_HOSTS='learnant.example.org,learnant.example.net',
            CSRF_TRUSTED_ORIGINS='https://learnant.example.org',
            DATABASE_URL='postgresql://user:pass@127.0.0.1:5432/learnant',
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_direct_local_development_can_use_sqlite_and_staticfiles_storage(self):
        result = self.run_settings_probe(
            """
from config import settings
assert settings.DEBUG is True
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
assert settings.ALLOWED_HOSTS == ['localhost', '127.0.0.1']
assert settings.STORAGES['staticfiles']['BACKEND'] == 'django.contrib.staticfiles.storage.StaticFilesStorage'
""",
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_railway_public_domain_is_added_as_exact_host_and_https_origin(self):
        result = self.run_settings_probe(
            """
from config import settings
assert settings.ALLOWED_HOSTS == ['localhost', 'learnant-production.up.railway.app']
assert settings.CSRF_TRUSTED_ORIGINS == ['https://learnant-production.up.railway.app']
""",
            DEBUG='false',
            SECRET_KEY='a-secure-test-key-that-is-not-used-for-any-real-data',
            ALLOWED_HOSTS='localhost',
            RAILWAY_PUBLIC_DOMAIN='learnant-production.up.railway.app',
            DATABASE_URL='postgresql://user:pass@127.0.0.1:5432/learnant',
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_refuses_development_secret_or_missing_database(self):
        no_secret = self.run_settings_probe(
            'from config import settings',
            DEBUG='false',
            ALLOWED_HOSTS='learnant.example.org',
            DATABASE_URL='postgresql://user:pass@127.0.0.1:5432/learnant',
        )
        no_database = self.run_settings_probe(
            'from config import settings',
            DEBUG='false',
            SECRET_KEY='a-secure-test-key-that-is-not-used-for-any-real-data',
            ALLOWED_HOSTS='learnant.example.org',
        )

        self.assertNotEqual(no_secret.returncode, 0)
        self.assertIn('SECRET_KEY', no_secret.stderr)
        self.assertNotEqual(no_database.returncode, 0)
        self.assertIn('DATABASE_URL', no_database.stderr)
