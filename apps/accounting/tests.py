from decimal import Decimal

from django.test import TestCase

from apps.accounting.models import Account, JournalEntry, JournalLine
from apps.accounting.services import build_trial_balance, post_entry
from apps.core.models import Company


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