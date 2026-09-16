from django.test import TestCase, Client
from django.urls import reverse

from apps.core.models import Company, Role, User


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('core:login')

    def test_login_page_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redirects_when_not_logged_in(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)


class AuthenticatedViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')

    def test_dashboard_redirects_to_reports(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_profile_page(self):
        response = self.client.get(reverse('core:profile'))
        self.assertEqual(response.status_code, 200)
