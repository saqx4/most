from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User


class ReportsViewTestMixin:
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')


class DashboardTest(ReportsViewTestMixin, TestCase):
    def test_dashboard_200(self):
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)


class TrialBalanceTest(ReportsViewTestMixin, TestCase):
    def test_page_200(self):
        response = self.client.get(reverse('reports:trial_balance'))
        self.assertEqual(response.status_code, 200)


class IncomeStatementTest(ReportsViewTestMixin, TestCase):
    def test_page_200(self):
        response = self.client.get(reverse('reports:income_statement'))
        self.assertEqual(response.status_code, 200)


class BalanceSheetTest(ReportsViewTestMixin, TestCase):
    def test_page_200(self):
        response = self.client.get(reverse('reports:balance_sheet'))
        self.assertEqual(response.status_code, 200)


class AccountBalancesTest(ReportsViewTestMixin, TestCase):
    def test_page_200(self):
        response = self.client.get(reverse('reports:account_balances'))
        self.assertEqual(response.status_code, 200)
