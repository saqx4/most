from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounting.models import Account, JournalEntry, JournalLine
from apps.core.models import Company

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='TestCo')

    def test_create_account(self):
        acc = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        self.assertEqual(acc.code, '1000')
        self.assertTrue(acc.is_active)

    def test_str_account(self):
        acc = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        self.assertEqual(str(acc), '1000 - Bank')

    def test_account_defaults(self):
        acc = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        self.assertTrue(acc.is_active)
        self.assertIsNone(acc.currency)
        self.assertEqual(acc.description, '')

    def test_create_journal_entry(self):
        je = JournalEntry.objects.create(
            company=self.company, memo='Test entry',
            status=JournalEntry.Status.DRAFT,
        )
        self.assertEqual(je.memo, 'Test entry')
        self.assertEqual(je.status, 'draft')

    def test_str_journal_entry(self):
        je = JournalEntry.objects.create(
            company=self.company, entry_number='JE-001',
            status=JournalEntry.Status.DRAFT,
        )
        self.assertEqual(str(je), 'JE-001')

    def test_journal_entry_defaults(self):
        je = JournalEntry.objects.create(
            company=self.company, status=JournalEntry.Status.DRAFT,
        )
        self.assertEqual(je.memo, '')
        self.assertEqual(je.reference, '')

    def test_create_journal_line(self):
        acc = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        je = JournalEntry.objects.create(
            company=self.company, status=JournalEntry.Status.DRAFT,
        )
        line = JournalLine.objects.create(
            entry=je, account=acc,
            debit=Decimal('100.00'), credit=Decimal('0.00'),
        )
        self.assertEqual(line.debit, Decimal('100.00'))

    def test_journal_line_str(self):
        acc = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        je = JournalEntry.objects.create(
            company=self.company, status=JournalEntry.Status.DRAFT,
        )
        line = JournalLine.objects.create(
            entry=je, account=acc,
            debit=Decimal('50.00'), credit=Decimal('0.00'),
        )
        self.assertIn('1000', str(line))

    def test_journal_line_defaults(self):
        acc = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        je = JournalEntry.objects.create(
            company=self.company, status=JournalEntry.Status.DRAFT,
        )
        line = JournalLine.objects.create(
            entry=je, account=acc,
            debit=Decimal('0.00'), credit=Decimal('0.00'),
        )
        self.assertEqual(line.description, '')


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testadmin', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        self.client.login(username='testadmin', password='testpass123')
        self.company = Company.objects.create(name='TestCo', is_default=True)

    def test_journal_list(self):
        resp = self.client.get(reverse('accounting:journal_list'))
        self.assertEqual(resp.status_code, 200)

    def test_journal_create(self):
        resp = self.client.get(reverse('accounting:journal_create'))
        self.assertEqual(resp.status_code, 200)

    def test_journal_delete(self):
        acc = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        je = JournalEntry.objects.create(
            company=self.company, status=JournalEntry.Status.DRAFT,
        )
        resp = self.client.post(reverse('accounting:journal_delete', args=[je.pk]))
        self.assertEqual(resp.status_code, 302)
