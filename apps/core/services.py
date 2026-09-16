from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import AuditLog, Company, Notification, NumberSequence

MONEY = dict(max_digits=14, decimal_places=2)


def get_company(user=None):
    if user is not None and getattr(user, 'company', None):
        return user.company
    return Company.objects.filter(is_default=True).first() or Company.objects.first()


def get_sequence_next(name, prefix=None, padding=4):
    """Return and increment a document number like INV-0007 (one per company)."""
    seq, _ = NumberSequence.objects.get_or_create(
        name=name, defaults={'prefix': prefix or name}
    )
    seq.last_number += 1
    seq.save(update_fields=['last_number', 'updated_at'])
    return f'{seq.prefix}-{seq.last_number:0{padding}d}'


def log_audit(user, action, model, object_id='', details=''):
    if user is not None and user.is_authenticated:
        AuditLog.objects.create(user=user, action=action, model=model, object_id=object_id, details=details)


def notify(user, title, message='', url=''):
    if user is not None:
        Notification.objects.create(user=user, title=title, message=message, url=url)


def ensure_default_accounting(company, rmb_diag=False):
    """Create the standard chart of accounts + tax rates for a company (idempotent)."""
    from apps.accounting.models import Account, TaxRate

    groups = [
        ('1000', 'Bank & Cash', 'asset'),
        ('1100', 'Accounts Receivable', 'asset'),
        ('1200', 'Inventory', 'asset'),
        ('1300', 'Fixed Assets', 'asset'),
        ('1400', 'Other Assets', 'asset'),
        ('2000', 'Accounts Payable', 'liability'),
        ('2100', 'Tax Liabilities', 'liability'),
        ('2200', 'Payroll Liabilities', 'liability'),
        ('2300', 'Long-term Liabilities', 'liability'),
        ('3000', 'Equity', 'equity'),
        ('4000', 'Income', 'income'),
        ('5000', 'Cost of Goods Sold', 'expense'),
        ('6000', 'Operating Expenses', 'expense'),
        ('7000', 'Other Expenses', 'expense'),
    ]
    created = []
    for code, name, atype in groups:
        _, was_created = Account.objects.get_or_create(
            company=company, code=code, defaults={'name': name, 'type': atype}
        )
        if was_created:
            created.append(code)

    taxes = [
        ('VAT', Decimal('20.00')),
        ('ZERO', Decimal('0.00')),
    ]
    for code, rate in taxes:
        from apps.accounting.models import TaxRate as TR
        TR.objects.get_or_create(company=company, code=code, defaults={'name': code, 'rate': rate})

    if rmb_diag:
        for c in created:
            print('  created account', c)
    return created


def today():
    return timezone.localdate()


def money(value, digits=2):
    if value is None:
        return Decimal('0.00')
    return Decimal(value).quantize(Decimal('1.' + '0' * digits))