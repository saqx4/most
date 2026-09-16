from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import render
from django.utils import timezone

from apps.accounting import services as acc
from apps.core.decorators import roles_required
from apps.core.models import CompanyScoped
from apps.core.services import get_company


def _company(request):
    return get_company(request.user)


@login_required
def dashboard(request):
    company = _company(request)
    cache_key = f'dashboard_{request.user.pk}'
    data = cache.get(cache_key)
    if data is None:
        from apps.inventory.models import Product, StockLevel
        from apps.sales.models import SalesInvoice, SalesOrder
        from apps.purchasing.models import PurchaseOrder
        from decimal import Decimal

        invoices = SalesInvoice.objects.filter(company=company)
        open_invoices = invoices.filter(status__in=('posted', 'paid'))
        total_sales = sum(i.total for i in invoices.filter(status__in=('posted', 'paid'))) or Decimal('0.00')
        due_now = sum(i.amount_due for i in invoices.filter(status='posted')) or Decimal('0.00')
        low_stock = [p for p in Product.objects.filter(company=company, is_active=True) if p.on_hand <= p.reorder_point]
        recent = invoices.order_by('-id')[:6]

        today = timezone.localdate()
        monthly_revenue = []
        revenue_labels = []
        for i in range(5, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            year, month = month_date.year, month_date.month
            month_total = sum(
                inv.total for inv in invoices.filter(
                    invoice_date__year=year, invoice_date__month=month,
                    status__in=('posted', 'paid')
                )
            ) or Decimal('0.00')
            monthly_revenue.append(float(month_total))
            revenue_labels.append(month_date.strftime('%b %Y'))

        invoices_for_top = list(
            SalesInvoice.objects.filter(company=company, status__in=('posted', 'paid'))
            .select_related('customer')
        )
        customer_totals = {}
        for inv in invoices_for_top:
            name = inv.customer.name if inv.customer else 'Unknown'
            customer_totals[name] = customer_totals.get(name, Decimal('0')) + inv.total
        top_customers = sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)[:5]

        ar_aging_buckets = {'0-30': Decimal('0'), '31-60': Decimal('0'), '61-90': Decimal('0'), '90+': Decimal('0')}
        for inv in invoices.filter(status='posted'):
            if inv.due_date:
                days = (today - inv.due_date).days
                due = inv.amount_due
                if days <= 30:
                    ar_aging_buckets['0-30'] += due
                elif days <= 60:
                    ar_aging_buckets['31-60'] += due
                elif days <= 90:
                    ar_aging_buckets['61-90'] += due
                else:
                    ar_aging_buckets['90+'] += due

        stock_levels = StockLevel.objects.filter(company=company)
        inventory_value = sum(
            (sl.quantity * sl.avg_cost for sl in stock_levels), Decimal('0.00')
        )

        pending_pos = PurchaseOrder.objects.filter(
            company=company, status__in=('draft', 'confirmed')
        )
        pending_po_count = pending_pos.count()
        pending_po_total = sum(po.total for po in pending_pos) or Decimal('0.00')

        data = {
            'company': company,
            'total_sales': total_sales,
            'due_now': due_now,
            'low_stock': low_stock[:5],
            'recent_invoices': recent,
            'monthly_revenue': monthly_revenue,
            'revenue_labels': revenue_labels,
            'top_customers': top_customers,
            'ar_aging_0_30': ar_aging_buckets['0-30'],
            'ar_aging_31_60': ar_aging_buckets['31-60'],
            'ar_aging_61_90': ar_aging_buckets['61-90'],
            'ar_aging_90_plus': ar_aging_buckets['90+'],
            'inventory_value': inventory_value,
            'pending_po_count': pending_po_count,
            'pending_po_total': pending_po_total,
        }
        cache.set(cache_key, data, 120)  # cache 2 minutes
    else:
        data['company'] = _company(request)

    return render(request, 'apps/reports/dashboard.html', data)


def invalidate_dashboard_cache(user_id):
    cache.delete(f'dashboard_{user_id}')


@login_required
@roles_required('accountant', 'admin')
def trial_balance(request):
    company = _company(request)
    cache_key = f'trial_balance_{company.pk}'
    rows = cache.get(cache_key)
    if rows is None:
        rows = acc.build_trial_balance(company)
        cache.set(cache_key, rows, 120)
    return render(request, 'apps/reports/trial_balance.html', {'rows': rows})


@login_required
@roles_required('accountant', 'admin')
def income_statement(request):
    company = _company(request)
    cache_key = f'income_stmt_{company.pk}'
    data = cache.get(cache_key)
    if data is None:
        data = acc.build_income_statement(company)
        cache.set(cache_key, data, 120)
    return render(request, 'apps/reports/income_statement.html', {'data': data})


@login_required
@roles_required('accountant', 'admin')
def balance_sheet(request):
    company = _company(request)
    cache_key = f'balance_sheet_{company.pk}'
    data = cache.get(cache_key)
    if data is None:
        data = acc.build_balance_sheet(company)
        cache.set(cache_key, data, 120)
    return render(request, 'apps/reports/balance_sheet.html', {'data': data})


@login_required
@roles_required('accountant', 'admin')
def account_balances_view(request):
    company = _company(request)
    rows = acc.account_balances(company)
    return render(request, 'apps/reports/account_balances.html', {'rows': rows})
