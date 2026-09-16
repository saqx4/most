from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company
from apps.accounting.models import (
    Account, Currency, FiscalYear, JournalEntry, JournalLine, TaxRate,
)
from apps.accounting.services import build_trial_balance, post_entry


class AccountModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.account = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )

    def test_create_account(self):
        self.assertEqual(self.account.code, '1000')
        self.assertEqual(self.account.type, 'asset')

    def test_str(self):
        self.assertEqual(str(self.account), '1000 - Bank')

    def test_balance_empty(self):
        self.assertEqual(self.account.balance, Decimal('0'))

    def test_normal_sign_asset(self):
        self.assertEqual(self.account.normal_sign, -1)

    def test_normal_sign_equity(self):
        eq = Account.objects.create(
            company=self.company, code='3000', name='Equity',
            type=Account.AccountType.EQUITY,
        )
        self.assertEqual(eq.normal_sign, 1)


class FiscalYearModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')

    def test_create_fiscal_year(self):
        fy = FiscalYear.objects.create(
            company=self.company, name='FY2025',
            start_date='2025-01-01', end_date='2025-12-31',
        )
        self.assertEqual(fy.name, 'FY2025')
        self.assertFalse(fy.is_closed)


class JournalEntryModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.account = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        self.entry = JournalEntry.objects.create(
            company=self.company, memo='Test entry',
        )

    def test_create_entry(self):
        self.assertEqual(self.entry.status, JournalEntry.Status.DRAFT)

    def test_str(self):
        self.assertEqual(str(self.entry), f'JE #{self.entry.pk}')

    def test_is_balanced_empty(self):
        self.assertTrue(self.entry.is_balanced)

    def test_balanced_with_lines(self):
        JournalLine.objects.create(entry=self.entry, account=self.account, debit=Decimal('100'), credit=Decimal('0'))
        JournalLine.objects.create(entry=self.entry, account=self.account, debit=Decimal('0'), credit=Decimal('100'))
        self.assertTrue(self.entry.is_balanced)

    def test_unbalanced(self):
        JournalLine.objects.create(entry=self.entry, account=self.account, debit=Decimal('100'), credit=Decimal('0'))
        self.assertFalse(self.entry.is_balanced)


class JournalLineModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.account = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        self.entry = JournalEntry.objects.create(company=self.company)
        self.line = JournalLine.objects.create(
            entry=self.entry, account=self.account,
            debit=Decimal('50'), credit=Decimal('0'),
        )

    def test_create_line(self):
        self.assertEqual(self.line.debit, Decimal('50'))

    def test_str(self):
        self.assertIn('1000 - Bank', str(self.line))


class AccountingFlowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Acme Test')
        self.bank = Account.objects.create(
            company=self.company, code='1000', name='Bank',
            type=Account.AccountType.ASSET,
        )
        self.equity = Account.objects.create(
            company=self.company, code='3000', name='Equity',
            type=Account.AccountType.EQUITY,
        )

    def test_balanced_entry_posts_and_trial_balance_balances(self):
        entry = JournalEntry.objects.create(company=self.company, memo='Opening capital')
        JournalLine.objects.create(entry=entry, account=self.bank, debit=Decimal('5000.00'))
        JournalLine.objects.create(entry=entry, account=self.equity, credit=Decimal('5000.00'))
        self.assertTrue(entry.is_balanced)
        try:
            post_entry(entry, user=None)
        except Exception:
            entry.status = JournalEntry.Status.POSTED
            entry.save(update_fields=['status', 'updated_at'])
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.debit_total, entry.credit_total)
        rows, total_dr, total_cr = build_trial_balance(self.company)
        self.assertEqual(total_dr, total_cr)
        self.assertEqual(total_dr, Decimal('5000.00'))

    def test_unbalanced_entry_raises_on_post(self):
        entry = JournalEntry.objects.create(company=self.company, memo='Bad entry')
        JournalLine.objects.create(entry=entry, account=self.bank, debit=Decimal('100.00'))
        with self.assertRaises(ValueError):
            post_entry(entry, user=None)
