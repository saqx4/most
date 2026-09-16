#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Ensuring admin user..."
python manage.py ensure_admin --password "${ADMIN_PASSWORD:-admin12345}"

echo "Starting server..."
exec gunicorn erp.wsgi:application --config gunicorn_config.py
