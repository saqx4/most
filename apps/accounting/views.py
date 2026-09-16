from decimal import Decimal
from urllib import parse as urlparse

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounting import forms
from apps.accounting import services as acc
from apps.accounting.models import Account, FiscalYear, JournalEntry, JournalLine
from apps.core.decorators import roles_required
from apps.core.models import Company, CompanyScoped, User
from apps.core.services import get_company


def _company(request):
    return get_company(request.user)


# ---------------------------------------------------------------------------
# Dashboard / landing
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    company = _company(request)
    now = timezone.localdate()
    from apps.sales.models import SalesOrder, SalesInvoice
    from apps.inventory.models import Product
    open_inv = SalesInvoice.objects.filter(company=company, status='posted')
    due_now = sum(i.amount_due for i in open_inv)
    orders_this_month = SalesOrder.objects.filter(company=company, order_date__year=now.year, order_date__month=now.month).count()
    low_stock = [p for p in Product.objects.filter(company=company, is_active=True, is_tracked=True) if p.on_hand <= p.reorder_point]
    recent_invoices = open_inv[:6]
    return render(request, 'apps/accounting/dashboard.html', {
        'company': company, 'due_now': due_now, 'orders_this_month': orders_this_month,
        'low_stock': low_stock, 'recent_invoices': recent_invoices,
    })


# ---------------------------------------------------------------------------
# General ledger / AR ledger
# ---------------------------------------------------------------------------
@login_required
@roles_required('accountant', 'admin')
def general_ledger(request):
    company = _company(request)
    q = request.GET.get('q', '').strip()
    account_id = request.GET.get('account', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    lines = acc.journal_lines_filtered(company, posted_only=True, account=account_id or None, start=start or None, end=end or None)
    if q:
        lines = [l for l in lines if q.lower() in (l.description or '').lower() or q.lower() in (l.account.code + ' ' + l.account.name).lower()]
    accounts = Account.objects.filter(company=company, is_active=True)
    return render(request, 'apps/accounting/general_ledger.html', {
        'lines': lines, 'q': q, 'accounts': accounts, 'account_id': account_id,
        'start': start, 'end': end,
    })


@login_required
@roles_required('accountant', 'admin')
def ar_ledger(request):
    company = _company(request)
    lines = acc.journal_lines_filtered(company, posted_only=True).filter(account__type=Account.AccountType.ASSET)
    return render(request, 'apps/accounting/general_ledger.html', {
        'lines': lines, 'q': '', 'accounts': [], 'account_id': '', 'start': '', 'end': '', 'ar_mode': True,
    })


# ---------------------------------------------------------------------------
# Journal entries
# ---------------------------------------------------------------------------
@login_required
@roles_required('accountant', 'admin')
def journal_list(request):
    company = _company(request)
    entries = JournalEntry.objects.filter(company=company).order_by('-date', '-id')
    return render(request, 'apps/accounting/journal_list.html', {'entries': entries})


@login_required
@roles_required('accountant', 'admin')
def journal_detail(request, entry_id):
    from django.shortcuts import get_object_or_404
    company = _company(request)
    entry = get_object_or_404(JournalEntry, pk=entry_id, company=company)
    debits = entry.lines.filter(debit__gt=0)
    credits = entry.lines.filter(credit__gt=0)
    return render(request, 'apps/accounting/journal_detail.html', {
        'entry': entry, 'debits': debits, 'credits': credits,
    })


@login_required
@roles_required('accountant', 'admin')
def journal_create(request):
    company = _company(request)
    form = forms.JournalEntryForm(
        request.POST or None, company=company,
        initial={'date': timezone.localdate(), 'fiscal_year': FiscalYear.objects.filter(company=company).first()},
    )
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.company = company
        entry.status = JournalEntry.Status.DRAFT
        entry.created_by = request.user
        entry.save()
        for d in form.cleaned_data.get('lines', []):
            JournalLine.objects.create(
                entry=entry, account=d['account'], debit=d['debit'], credit=d['credit'], description=d.get('description', ''),
            )
        if entry.debit_total != entry.credit_total:
            entry.delete()
            messages.error(request, 'Entry not balanced (debits != credits).')
        else:
            messages.success(request, 'Draft journal entry created.')
            return redirect('accounting:journal_detail', entry_id=entry.pk)
    return render(request, 'apps/accounting/journal_form.html', {'form': form})


@login_required
@roles_required('accountant', 'admin')
def journal_edit(request, entry_id):
    from django.shortcuts import get_object_or_404
    company = _company(request)
    entry = get_object_or_404(JournalEntry, pk=entry_id, company=company)
    if entry.status != JournalEntry.Status.DRAFT:
        messages.error(request, 'Only draft entries can be edited.')
        return redirect('accounting:journal_detail', entry_id=entry.pk)
    initial_lines = [
        {'account': l.account_id, 'debit': float(l.debit or 0), 'credit': float(l.credit or 0), 'description': l.description or ''}
        for l in entry.lines.all()
    ]
    form = forms.JournalEntryForm(
        request.POST or None, instance=entry, company=company,
        initial={'date': entry.date, 'fiscal_year': entry.fiscal_year, 'lines': initial_lines},
    )
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.save()
        entry.lines.all().delete()
        for d in form.cleaned_data.get('lines', []):
            JournalLine.objects.create(
                entry=entry, account=d['account'], debit=d['debit'], credit=d['credit'], description=d.get('description', ''),
            )
        if entry.debit_total != entry.credit_total:
            messages.error(request, 'Entry not balanced (debits != credits).')
        else:
            messages.success(request, 'Journal entry updated.')
            return redirect('accounting:journal_detail', entry_id=entry.pk)
    return render(request, 'apps/accounting/journal_form.html', {'form': form, 'editing': True})


@login_required
@require_POST
@roles_required('accountant', 'admin')
def journal_delete(request, entry_id):
    from django.shortcuts import get_object_or_404
    company = _company(request)
    entry = get_object_or_404(JournalEntry, pk=entry_id, company=company)
    if entry.status != JournalEntry.Status.DRAFT:
        messages.error(request, 'Only draft entries can be deleted.')
        return redirect('accounting:journal_detail', entry_id=entry.pk)
    entry.delete()
    messages.success(request, 'Journal entry deleted.')
    return redirect('accounting:journal_list')


@login_required
@roles_required('accountant', 'admin')
def journal_post(request, entry_id):
    from django.shortcuts import get_object_or_404
    company = _company(request)
    entry = get_object_or_404(JournalEntry, pk=entry_id, company=company)
    try:
        acc.post_entry(entry, user=request.user)
        messages.success(request, f'{entry} posted.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('accounting:journal_detail', entry_id=entry.pk)


@login_required
@require_POST
@roles_required('accountant', 'admin')
def close_year(request, fy_id):
    from django.shortcuts import get_object_or_404
    company = _company(request)
    fy = get_object_or_404(FiscalYear, pk=fy_id, company=company)
    if fy.is_closed:
        messages.warning(request, 'Fiscal year is already closed.')
    else:
        try:
            acc.close_fiscal_year(fy)
            messages.success(request, f'Fiscal year "{fy.name}" closed.')
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect('accounting:dashboard')


@login_required
@roles_required('accountant', 'admin')
def journal_void(request, entry_id):
    company = _company(request)
    entry = get_object_or_404(JournalEntry, pk=entry_id, company=company)
    if entry.status == JournalEntry.Status.POSTED:
        messages.error(request, 'A posted entry must be reversed, not voided.')
    else:
        entry.status = JournalEntry.Status.VOID
        entry.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'{entry} voided.')
    return redirect('accounting:journal_detail', entry_id=entry.pk)
