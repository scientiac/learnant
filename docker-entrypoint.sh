#!/bin/sh
set -eu

if [ "$(id -u)" -eq 0 ]; then
  mkdir -p /app/uploads /app/staticfiles
  chown learnant:learnant /app/uploads /app/staticfiles
  exec gosu learnant "$0" "$@"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-3}" --no-control-socket --access-logfile - --error-logfile -
