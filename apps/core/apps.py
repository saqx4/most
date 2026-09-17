from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        import apps.core.cache_signals  # noqa: F401
        self._ensure_admin()

    def _ensure_admin(self):
        """Create admin user automatically if missing."""
        import os
        import logging
        logger = logging.getLogger('erp')
        try:
            from apps.core.models import Company, Role, User
            if not User.objects.filter(username='admin').exists():
                company, _ = Company.objects.get_or_create(
                    name=os.environ.get('COMPANY_NAME', 'My Company'),
                    defaults={
                        'legal_name': os.environ.get('COMPANY_NAME', 'My Company'),
                        'base_currency': 'USD',
                        'is_default': True,
                        'is_active': True,
                    },
                )
                for choice in Role.RoleChoices:
                    Role.objects.get_or_create(
                        code=choice.value,
                        defaults={'name': choice.label, 'description': ''},
                    )
                pw = os.environ.get('ADMIN_PASSWORD', 'admin12345')
                admin = User.objects.create_superuser('admin', 'admin@example.com', pw)
                admin.role = Role.objects.get(code='admin')
                admin.company = company
                admin.save()
                logger.info('Admin user created on startup.')
        except Exception as exc:
            logger.warning(f'ensure_admin on startup failed: {exc}')