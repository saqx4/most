from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalLine, TaxRate
from apps.core.models import AuditLog, User

ZERO = Decimal('0.00')
MONEY = dict(max_digits=14, decimal_places=2)


# ---------------------------------------------------------------------------
# Default structures (idempotent)
# ---------------------------------------------------------------------------
def ensure_chart_of_accounts(company):
    groups = [
        ('1000', 'Bank & Cash', 'asset'), ('1100', 'Accounts Receivable', 'asset'),
        ('1200', 'Inventory', 'asset'), ('1300', 'Fixed Assets', 'asset'),
        ('1400', 'Other Assets', 'asset'), ('2000', 'Accounts Payable', 'liability'),
        ('2100', 'Tax Liabilities', 'liability'), ('2200', 'Other Liabilities', 'liability'),
        ('3000', 'Equity', 'equity'), ('4000', 'Income', 'income'),
        ('5000', 'Cost of Goods Sold', 'expense'), ('6000', 'Operating Expenses', 'expense'),
        ('7000', 'Other Expenses', 'expense'),
    ]
    created = []
    for code, name, atype in groups:
        a, made = Account.objects.get_or_create(
            company=company, code=code, defaults={'name': name, 'type': atype, 'is_active': True}
        )
        if made:
            created.append(code)
    tax, _ = TaxRate.objects.get_or_create(
        company=company, code='VAT', defaults={'name': 'VAT', 'rate': Decimal('20.00')}
    )
    return created


def find_account(company, code):
    return Account.objects.filter(company=company, code=code).first()


def get_default_account(company, code):
    return find_account(company, code)


def account_balance(account, as_of=None):
    return account_balances(account.company, as_of=as_of).get(account.pk, ZERO)


def account_balances(company, as_of=None):
    """account_id -> signed posted balance (debits minus credits)."""
    lines = JournalLine.objects.filter(entry__company=company, entry__status=JournalEntry.Status.POSTED)
    if as_of:
        lines = lines.filter(entry__date__lte=as_of)
    rows = lines.values('account_id').annotate(d=Sum('debit'), c=Sum('credit'))
    out = {}
    for r in rows:
        out[r['account_id']] = (r['d'] or ZERO) - (r['c'] or ZERO)
    return out


def post_entry(entry, user=None):
    """Post a balanced journal entry atomically."""
    from django.db import transaction as dj_transaction
    if entry.status == JournalEntry.Status.POSTED:
        return entry
    if entry.status == JournalEntry.Status.VOID:
        raise ValueError('Cannot post a void entry.')
    if entry.debit_total != entry.credit_total:
        raise ValueError('Entry not balanced.')
    with dj_transaction.atomic():
        entry.status = JournalEntry.Status.POSTED
        entry.posted_at = timezone.now()
        entry.save(update_fields=['status', 'posted_at', 'updated_at'])
    if user:
        AuditLog.objects.create(
            user=user, action='post', model='JournalEntry', object_id=entry.pk,
            details=f'Posted {entry}', company=entry.company,
        )
    return entry


def void_entry(entry, user=None):
    from django.db import transaction as dj_transaction
    if entry.status == JournalEntry.Status.VOID:
        return entry
    if entry.status == JournalEntry.Status.POSTED:
        raise ValueError('Posted entries must be reversed, not voided.')
    with dj_transaction.atomic():
        entry.status = JournalEntry.Status.VOID
        entry.save(update_fields=['status', 'updated_at'])
    return entry


def build_trial_balance(company, as_of=None, fiscal_year=None):
    balances = account_balances(company, as_of=as_of)
    accounts = list(Account.objects.filter(company=company, is_active=True).order_by('code'))
    rows, total_dr, total_cr = [], ZERO, ZERO
    for a in accounts:
        raw = balances.get(a.pk, ZERO)
        if a.type in (Account.AccountType.ASSET, Account.AccountType.EXPENSE):
            dr = raw if raw >= 0 else ZERO
            cr = -raw if raw < 0 else ZERO
        else:
            cr = raw if raw >= 0 else ZERO
            dr = -raw if raw < 0 else ZERO
        total_dr += dr
        total_cr += cr
        rows.append({'account': a, 'debit': dr, 'credit': cr, 'balance': raw})
    return rows, total_dr, total_cr


def build_income_statement(company, as_of=None, fiscal_year=None):
    balances = account_balances(company, as_of=as_of)
    income, expenses = [], []
    for a in Account.objects.filter(company=company, is_active=True):
        raw = balances.get(a.pk, ZERO)
        if a.type == Account.AccountType.INCOME:
            income.append({'account': a, 'amount': raw})
        elif a.type == Account.AccountType.EXPENSE:
            expenses.append({'account': a, 'amount': raw})
    income.sort(key=lambda r: -r['amount'])
    expenses.sort(key=lambda r: -r['amount'])
    ti = sum((r['amount'] for r in income), ZERO)
    te = sum((r['amount'] for r in expenses), ZERO)
    return income, expenses, ti, te, ti - te


def build_balance_sheet(company, as_of=None):
    balances = account_balances(company, as_of=as_of)
    assets, liabilities, equity = [], [], []
    for a in Account.objects.filter(company=company, is_active=True):
        raw = balances.get(a.pk, ZERO)
        if a.type == Account.AccountType.ASSET:
            assets.append({'account': a, 'amount': raw})
        elif a.type == Account.AccountType.LIABILITY:
            liabilities.append({'account': a, 'amount': raw})
        elif a.type == Account.AccountType.EQUITY:
            equity.append({'account': a, 'amount': raw})
    ta = sum((r['amount'] for r in assets), ZERO)
    tl = sum((r['amount'] for r in liabilities), ZERO)
    te = sum((r['amount'] for r in equity), ZERO)
    return {'assets': assets, 'liabilities': liabilities, 'equity': equity,
            'total_assets': ta, 'total_liabilities': tl, 'total_equity': te,
            'difference': ta - tl - te}


def aging_buckets(items, ref_date=None):
    ref = ref_date or timezone.localdate()
    out = {'current': ZERO, '30': ZERO, '60': ZERO, '90': ZERO, '+90': ZERO}
    for item in items:
        due = item.get('due')
        open_amt = item.get('open', ZERO)
        days = (ref - due).days if due else 0
        if not due:
            out['current'] += open_amt
        elif days <= 0:
            out['current'] += open_amt
        elif days <= 30:
            out['30'] += open_amt
        elif days <= 60:
            out['60'] += open_amt
        elif days <= 90:
            out['90'] += open_amt
        else:
            out['+90'] += open_amt
    return out


def ensure_default_accounting(company, rmb_diag=False):
    """Alias kept for core.services compatibility. Delegates to ensure_chart_of_accounts."""
    return ensure_chart_of_accounts(company)


def log_audit(request, action, model, object_id, details=''):
    if request and getattr(request, 'user', None) and request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user, action=action, model=model, object_id=str(object_id), details=details,
            company=request.user.company_id,
        )


def close_fiscal_year(fiscal_year):
    """Close a fiscal year: validate all entries are posted, mark as closed."""
    draft = JournalEntry.objects.filter(fiscal_year=fiscal_year, status='draft')
    if draft.exists():
        raise ValueError(f'{draft.count()} draft entries remain')
    fiscal_year.is_closed = True
    fiscal_year.save()


def reverse_journal_entry(entry, reason=''):
    """Create a reversing entry for a posted journal entry."""
    from django.db import transaction as dj_transaction
    with dj_transaction.atomic():
        reversing = JournalEntry.objects.create(
            date=entry.date,
            memo=f'Reversal of {entry.entry_number}: {reason}',
            reference=f'REV-{entry.entry_number}',
            created_by=entry.created_by,
            fiscal_year=entry.fiscal_year,
            company=entry.company,
        )
        for line in entry.lines.all():
            JournalLine.objects.create(
                entry=reversing,
                account=line.account,
                debit=line.credit,
                credit=line.debit,
                description=f'Reversal: {line.description}',
            )
        return reversing


def journal_lines_filtered(company, *, posted_only=True, account=None, start=None, end=None, q=None, limit=500):
    """Return posted JournalLine rows for a company, optionally filtered."""
    from apps.accounting.models import JournalLine, JournalEntry
    qs = JournalLine.objects.filter(entry__company=company)
    if posted_only:
        qs = qs.filter(entry__status=JournalEntry.Status.POSTED)
    if account:
        qs = qs.filter(account_id=account.id if hasattr(account, 'id') else account)
    if start:
        qs = qs.filter(entry__date__gte=start)
    if end:
        qs = qs.filter(entry__date__lte=end)
    if q:
        qs = qs.filter(description__icontains=q)
    return qs.order_by('entry__date', 'entry__id')
