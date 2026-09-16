#!/usr/bin/env bash
# build.sh — Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Create superuser if it doesn't exist
python manage.py shell -c "
from apps.core.models import User, Company, Role
import os

# Ensure company
company, _ = Company.objects.get_or_create(
    name=os.environ.get('COMPANY_NAME', 'My Company'),
    defaults={
        'legal_name': os.environ.get('COMPANY_NAME', 'My Company'),
        'base_currency': 'USD',
        'is_default': True,
        'is_active': True,
    }
)

# Ensure roles
for choice in Role.RoleChoices:
    Role.objects.get_or_create(code=choice.value, defaults={'name': choice.label, 'description': ''})

# Create admin superuser
admin_pw = os.environ.get('ADMIN_PASSWORD', 'admin12345')
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@example.com', admin_pw)
    admin.role = Role.objects.get(code='admin')
    admin.company = company
    admin.save()
    print(f'Created admin user (password={admin_pw})')
else:
    print('Admin user already exists')
" 2>&1 || true
