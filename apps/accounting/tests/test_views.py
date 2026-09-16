from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User
from apps.accounting.models import Account, JournalEntry


class AccountingViewTestMixin:
    """Mixin that sets up a logged-in admin user with a company."""

    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')
        self.account = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )


class AccountingDashboardTest(AccountingViewTestMixin, TestCase):
    def test_dashboard_200(self):
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)


class GeneralLedgerTest(AccountingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('accounting:general_ledger'))
        self.assertEqual(response.status_code, 200)


class ARLedgerTest(AccountingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('accounting:ar_ledger'))
        self.assertEqual(response.status_code, 200)


class JournalListTest(AccountingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('accounting:journal_list'))
        self.assertEqual(response.status_code, 200)


class JournalDetailTest(AccountingViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.entry = JournalEntry.objects.create(
            company=self.company, memo='Test JE',
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('accounting:journal_detail', args=[self.entry.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_404(self):
        response = self.client.get(
            reverse('accounting:journal_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)


class JournalCreateTest(AccountingViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('accounting:journal_create'))
        self.assertEqual(response.status_code, 200)


class JournalDeleteTest(AccountingViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.entry = JournalEntry.objects.create(
            company=self.company, memo='To delete',
            status=JournalEntry.Status.DRAFT,
        )

    def test_delete_redirects(self):
        response = self.client.post(
            reverse('accounting:journal_delete', args=[self.entry.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(JournalEntry.objects.filter(pk=self.entry.pk).exists())
