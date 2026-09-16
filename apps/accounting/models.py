from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from apps.core.models import Company, CompanyScoped, TimeStampMixin, User

MONEY = dict(max_digits=14, decimal_places=2)


class Currency(TimeStampMixin):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=8, blank=True, default='')
    rate = models.DecimalField(**MONEY, default=Decimal('1.0000'))  # 1 unit = N base currency
    is_base = models.BooleanField(default=False)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.symbol}'.strip()


class FiscalYear(CompanyScoped):
    name = models.CharField(max_length=60)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_fy_name'),
        ]

    def __str__(self):
        return self.name


class AccountGroup(TimeStampMixin):
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='account_groups')
    position = models.IntegerField(default=0)

    class Meta:
        ordering = ['position', 'name']

    def __str__(self):
        return self.name


class TaxRate(CompanyScoped):
    name = models.CharField(max_length=80)
    rate = models.DecimalField(**MONEY, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.rate}%)'


class PaymentTerm(CompanyScoped):
    name = models.CharField(max_length=80)
    net_days = models.PositiveSmallIntegerField(default=30)
    cash_discount_days = models.PositiveSmallIntegerField(default=0)
    cash_discount_percent = models.DecimalField(**MONEY, default=Decimal('0.00'))

    class Meta:
        ordering = ['name']

    def __str__(self):
        label = f'Net {self.net_days}'
        if self.cash_discount_percent:
            label += f' / {self.cash_discount_percent}% in {self.cash_discount_days}'
        return label


class Account(CompanyScoped):
    class AccountType(models.TextChoices):
        ASSET = 'asset', 'Asset'
        LIABILITY = 'liability', 'Liability'
        EQUITY = 'equity', 'Equity'
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense'

    # For a normal (debit-natured) account the raw balance is reduced by credits.
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='uniq_account_code'),
        ]

    def __str__(self):
        return f'{self.code} - {self.name}'

    @property
    def balance(self):
        rows = self.entry_lines.aggregate(
            debits=models.Sum('debit'), credits=models.Sum('credit')
        )
        return (rows['debits'] or Decimal('0')) - (rows['credits'] or Decimal('0'))

    @property
    def normal_sign(self):
        # +1 if a credit raises the balance, -1 if a debit does
        return -1 if self.type in (Account.AccountType.ASSET, Account.AccountType.EXPENSE) else 1

    @property
    def signed_balance(self):
        return -self.normal_sign * self.balance


class JournalEntry(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        VOID = 'void', 'Void'

    entry_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    memo = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=100, blank=True)  # source document
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, null=True, blank=True, related_name='journal_entries')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries_created')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return self.entry_number or f'JE #{self.pk}'

    @property
    def debit_total(self):
        return sum((l.debit for l in self.lines.all()), Decimal('0'))

    @property
    def credit_total(self):
        return sum((l.credit for l in self.lines.all()), Decimal('0'))

    @property
    def is_balanced(self):
        return self.debit_total == self.credit_total


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='entry_lines')
    debit = models.DecimalField(**MONEY, default=Decimal('0.00'))
    credit = models.DecimalField(**MONEY, default=Decimal('0.00'))
    description = models.CharField(max_length=200, blank=True)

    # Optional partner (customer or supplier) for AR/AP reporting
    partner_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    partner_id = models.PositiveIntegerField(null=True, blank=True)
    partner = GenericForeignKey('partner_type', 'partner_id')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.account} {self.debit or self.credit}'