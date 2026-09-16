#!/usr/bin/env bash
# build.sh — Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py ensure_admin --password "${ADMIN_PASSWORD:-admin12345}"
