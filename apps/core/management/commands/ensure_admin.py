"""Create or update the admin superuser and default company.

Usage:
    python manage.py ensure_admin
    python manage.py ensure_admin --password mypassword
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Company, Role, User


class Command(BaseCommand):
    help = 'Create admin superuser, roles, and default company if missing.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='admin12345', help='Admin password')

    @transaction.atomic
    def handle(self, *args, **options):
        pw = options['password']

        # Company
        company, created = Company.objects.get_or_create(
            name='My Company',
            defaults={
                'legal_name': 'My Company',
                'base_currency': 'USD',
                'is_default': True,
                'is_active': True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created company: {company.name}'))

        # Roles
        for choice in Role.RoleChoices:
            Role.objects.get_or_create(
                code=choice.value,
                defaults={'name': choice.label, 'description': ''},
            )
        self.stdout.write('Roles ensured.')

        # Admin user
        if User.objects.filter(username='admin').exists():
            self.stdout.write('Admin user already exists.')
        else:
            admin = User.objects.create_superuser('admin', 'admin@example.com', pw)
            admin.role = Role.objects.get(code='admin')
            admin.company = company
            admin.save()
            self.stdout.write(self.style.SUCCESS(
                f'Admin created: username=admin password={pw}'
            ))
