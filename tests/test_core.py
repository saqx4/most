from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User

User = get_user_model()


class ModelTests(TestCase):
    def test_create_company(self):
        company = Company.objects.create(name='Acme Corp')
        self.assertEqual(company.name, 'Acme Corp')
        self.assertTrue(company.is_active)
        self.assertFalse(company.is_default)
        self.assertEqual(company.base_currency, 'USD')

    def test_str_company(self):
        company = Company.objects.create(name='Acme Corp')
        self.assertEqual(str(company), 'Acme Corp')

    def test_company_defaults(self):
        company = Company.objects.create(name='Test')
        self.assertEqual(company.legal_name, '')
        self.assertEqual(company.tax_id, '')
        self.assertEqual(company.phone, '')
        self.assertEqual(company.email, '')
        self.assertEqual(company.website, '')

    def test_create_role(self):
        role = Role.objects.create(code='admin', name='Administrator')
        self.assertEqual(role.code, 'admin')
        self.assertEqual(role.name, 'Administrator')

    def test_str_role(self):
        role = Role.objects.create(code='admin', name='Administrator')
        self.assertEqual(str(role), 'Administrator')

    def test_role_defaults(self):
        role = Role.objects.create(code='viewer', name='Viewer')
        self.assertEqual(role.description, '')

    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser', password='pass123', is_staff=True
        )
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_str_user(self):
        user = User.objects.create_user(
            username='testuser', password='pass123',
            first_name='John', last_name='Doe'
        )
        self.assertEqual(str(user), 'John Doe')

    def test_user_str_fallback_to_username(self):
        user = User.objects.create_user(username='testuser', password='pass123')
        self.assertEqual(str(user), 'testuser')


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testadmin', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        self.client.login(username='testadmin', password='testpass123')

    def test_login_page(self):
        resp = self.client.get(reverse('core:login'))
        self.assertEqual(resp.status_code, 200)
