from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import roles_required
from apps.core.services import get_company
from apps.inventory.models import StockMovement
from apps.sales import services as sal
from apps.sales.forms import (CustomerForm, InvoiceForm, InvoiceLineForm,
                              OrderForm, OrderLineForm, PaymentForm)
from apps.sales.models import (Customer, CustomerPayment, CreditNote, CreditNoteLine,
                               PeriodicInvoice, SalesInvoice, SalesInvoiceLine,
                               SalesOrder, SalesOrderLine, SalesQuote,
                               SalesQuoteLine, SalesSettings)


def _company(request):
    return get_company(request.user)


def _inline_formset(model, line_model, line_form, request, instance, company):
    from django.forms import inlineformset_factory
    factory = inlineformset_factory(model, line_model, form=line_form, extra=1, can_delete=True)
    return factory(request.POST or None, instance=instance, form_kwargs={'company': company})


def _open_invoices(company):
    return [i for i in SalesInvoice.objects.filter(company=company).select_related('customer', 'currency', 'tax')
            if i.status in ('draft', 'posted')]


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
@login_required
def customer_list(request):
    company = _company(request)
    qs = Customer.objects.filter(company=company)
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/sales/customer_list.html', {'page_obj': page, 'q': q})


@login_required
def customer_detail(request, pk):
    company = _company(request)
    customer = get_object_or_404(Customer, pk=pk, company=company)
    orders = customer.orders.all()[:10]
    invoices = customer.ar_invoices.all().select_related('tax')
    balance = sum(i.total - i.paid_total for i in invoices if i.status in ('posted', 'draft'))
    payments = customer.payments.all()[:10]
    return render(request, 'apps/sales/customer_detail.html', {
        'customer': customer, 'orders': orders, 'invoices': invoices,
        'balance': balance, 'payments': payments,
    })


@login_required
@roles_required('sales', 'accountant')
def customer_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('sales:customer_list')
    form = CustomerForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        form.save(company=company, user=request.user)
        messages.success(request, 'Customer created.')
        return redirect('sales:customer_list')
    return render(request, 'apps/sales/customer_form.html', {'form': form, 'title': 'New Customer'})


@login_required
@roles_required('sales', 'accountant')
def customer_edit(request, pk):
    company = _company(request)
    customer = get_object_or_404(Customer, pk=pk, company=company)
    form = CustomerForm(request.POST or None, instance=customer, company=company)
    if request.method == 'POST' and form.is_valid():
        form.save(company=company)
        messages.success(request, 'Customer updated.')
        return redirect('sales:customer_detail', pk=customer.pk)
    return render(request, 'apps/sales/customer_form.html', {'form': form, 'title': f'Edit {customer.name}'})


@login_required
@require_POST
@roles_required('sales', 'accountant')
def customer_delete(request, pk):
    company = _company(request)
    customer = get_object_or_404(Customer, pk=pk, company=company)
    customer_name = customer.name
    customer.delete()
    messages.success(request, f'Customer "{customer_name}" deleted.')
    return redirect('sales:customer_list')


# ---------------------------------------------------------------------------
# Sales orders
# ---------------------------------------------------------------------------
@login_required
def order_list(request):
    company = _company(request)
    qs = SalesOrder.objects.filter(company=company).select_related('customer')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/sales/order_list.html', {
        'page_obj': page, 'status': status,
        'statuses': SalesOrder.Status.choices,
    })


@login_required
def order_detail(request, pk):
    company = _company(request)
    order = get_object_or_404(SalesOrder.objects.select_related('customer', 'warehouse', 'currency', 'tax', 'salesperson'), pk=pk, company=company)
    return render(request, 'apps/sales/order_detail.html', {'order': order})


@login_required
@roles_required('sales', 'accountant')
def order_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('sales:order_list')
    form = OrderForm(request.POST or None, company=company)
    formset = _inline_formset(SalesOrder, SalesOrderLine, OrderLineForm, request, None, company)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        has_lines = any(l.cleaned_data and not l.cleaned_data.get('DELETE') for l in formset.forms)
        if not has_lines:
            messages.error(request, 'Add at least one line item.')
        else:
            order = form.save(commit=False)
            order.number = sal.next_number(company, 'SO')
            order.save()
            formset.instance = order
            formset.save()
            messages.success(request, f'Order {order.number} created.')
            return redirect('sales:order_detail', pk=order.pk)
    return render(request, 'apps/sales/order_form.html', {'form': form, 'formset': formset})


@login_required
@require_POST
@roles_required('sales', 'accountant')
def order_confirm(request, pk):
    company = _company(request)
    order = get_object_or_404(SalesOrder, pk=pk, company=company)
    try:
        sal.confirm_order(order, user=request.user)
        messages.success(request, f'Order {order.number} confirmed and sales journal entry posted.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('sales:order_detail', pk=order.pk)


# ---------------------------------------------------------------------------
# Sales invoices
# ---------------------------------------------------------------------------
@login_required
def invoice_list(request):
    company = _company(request)
    qs = SalesInvoice.objects.filter(company=company).select_related('customer')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/sales/invoice_list.html', {
        'page_obj': page, 'status': status,
        'statuses': SalesInvoice.Status.choices,
    })


@login_required
def invoice_detail(request, pk):
    company = _company(request)
    invoice = get_object_or_404(SalesInvoice.objects.select_related('customer', 'order', 'currency', 'tax'), pk=pk, company=company)
    payments = invoice.allocations.select_related('payment')

    from apps.core.services import generate_zatca_qr
    tax_amt = Decimal('0.00')
    for l in invoice.lines.all():
        if getattr(l, 'tax', None):
            tax_amt += l.line_total * (l.tax.rate / Decimal('100.00'))
    qr_data_uri = generate_zatca_qr(
        seller_name=company.name if company else 'ERP',
        tax_no=company.tax_id if company else '',
        timestamp_iso=f'{invoice.invoice_date}T12:00:00Z',
        total_amount=invoice.total,
        tax_amount=tax_amt,
    )

    return render(request, 'apps/sales/invoice_detail.html', {
        'invoice': invoice, 'payments': payments, 'qr_data_uri': qr_data_uri,
        'stock_movements': StockMovement.objects.filter(
            company=company, reference_type='SALES_DELIVERY', reference_id=invoice.pk),
    })


@login_required
@roles_required('sales', 'accountant')
def invoice_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('sales:invoice_list')
    form = InvoiceForm(request.POST or None, company=company)
    formset = _inline_formset(SalesInvoice, SalesInvoiceLine, InvoiceLineForm, request, None, company)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        has_lines = any(l.cleaned_data and not l.cleaned_data.get('DELETE') for l in formset.forms)
        if not has_lines:
            messages.error(request, 'Add at least one line item.')
        else:
            invoice = form.save(commit=False)
            invoice.number = sal.next_number(company, 'INV')
            invoice.status = SalesInvoice.Status.DRAFT
            invoice.save()
            formset.instance = invoice
            formset.save()

            # If marked paid upfront ("مدفوع بالفعل"), record payment and allocate immediately
            if invoice.is_paid_upfront and invoice.upfront_payment_amount > Decimal('0.00'):
                try:
                    pay_amt = invoice.upfront_payment_amount
                    payment = CustomerPayment.objects.create(
                        company=company,
                        number=sal.next_number(company, 'RCPT'),
                        customer=invoice.customer,
                        date=invoice.invoice_date,
                        amount=pay_amt,
                        method=invoice.upfront_payment_method or 'cash',
                        reference=invoice.upfront_payment_reference or f'Inv #{invoice.number}',
                        notes=f'Upfront payment for Invoice {invoice.number}',
                        status=CustomerPayment.Status.RECEIVED,
                        created_by=request.user,
                        posted_at=timezone.now()
                    )
                    sal.ARPaymentAllocation.objects.create(
                        payment=payment,
                        invoice=invoice,
                        allocated=pay_amt
                    )
                    if invoice.amount_due <= Decimal('0.00'):
                        invoice.status = SalesInvoice.Status.PAID
                        invoice.save(update_fields=['status'])
                except Exception as p_err:
                    messages.warning(request, f'Invoice saved, but upfront payment allocation failed: {p_err}')

            messages.success(request, f'Invoice {invoice.number} created successfully.')
            return redirect('sales:invoice_detail', pk=invoice.pk)
    return render(request, 'apps/sales/invoice_form.html', {'form': form, 'formset': formset})


@login_required
@require_POST
@roles_required('sales', 'accountant')
def invoice_mark_paid(request, pk):
    company = _company(request)
    invoice = get_object_or_404(SalesInvoice.objects.select_related('customer'), pk=pk, company=company)
    try:
        payment = sal.pay_invoice(invoice, user=request.user)
        if invoice.warehouse:
            from apps.inventory.services import apply_stock_movement
            from apps.inventory.models import StockMovement
            for line in invoice.lines.all():
                if line.quantity > 0:
                    apply_stock_movement(
                        company, product=line.product, warehouse=invoice.warehouse,
                        quantity=-line.quantity, unit_cost=line.product.avg_cost or Decimal('0.00'),
                        movement_type=StockMovement.MovementType.SALES_OUT,
                        reference_type='SALES_INVOICE', reference_id=invoice.pk,
                        reference_number=invoice.number, notes=f'Auto-deduct from invoice {invoice.number}',
                        user=request.user,
                    )
        messages.success(request, f'Invoice {invoice.number} marked paid (payment {payment.number}).')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('sales:invoice_detail', pk=invoice.pk)


@login_required
@roles_required('sales', 'accountant')
def payment_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('sales:invoice_list')
    form = PaymentForm(request.POST or None, company=company)
    open_invoices = _open_invoices(company) if request.method == 'GET' else []
    if request.method == 'POST' and form.is_valid():
        payment = form.save(company=company, user=request.user)
        try:
            allocations = sal.post_customer_payment(payment, user=request.user)
            messages.success(request, f'Payment {payment.number} allocated to {len(allocations)} invoice(s).')
            return redirect('sales:customer_detail', pk=payment.customer.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
    return render(request, 'apps/sales/payment_form.html', {
        'form': form, 'open_invoices': open_invoices,
    })


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------
@login_required
def quote_list(request):
    company = _company(request)
    qs = SalesQuote.objects.filter(company=company).select_related('customer')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/sales/quote_list.html', {
        'page_obj': page, 'status': status,
        'statuses': SalesQuote.Status.choices,
    })


@login_required
def quote_detail(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote.objects.select_related('customer', 'currency', 'salesperson'), pk=pk, company=company)
    return render(request, 'apps/sales/quote_detail.html', {'quote': quote})


@login_required
@roles_required('sales', 'accountant')
def quote_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('sales:quote_list')
    from apps.sales.forms import QuoteForm, QuoteLineForm
    form = QuoteForm(request.POST or None, company=company)
    formset = _inline_formset(SalesQuote, SalesQuoteLine, QuoteLineForm, request, None, company)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        has_lines = any(l.cleaned_data and not l.cleaned_data.get('DELETE') for l in formset.forms)
        if not has_lines:
            messages.error(request, 'Add at least one line item.')
        else:
            quote = form.save(commit=False)
            quote.number = sal.next_number(company, 'QOT')
            quote.status = SalesQuote.Status.DRAFT
            quote.save()
            formset.instance = quote
            formset.save()
            messages.success(request, f'Quote {quote.number} created.')
            return redirect('sales:quote_detail', pk=quote.pk)
    return render(request, 'apps/sales/quote_form.html', {'form': form, 'formset': formset})


@login_required
@require_POST
@roles_required('sales', 'accountant')
def quote_send(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote, pk=pk, company=company)
    if quote.status == SalesQuote.Status.DRAFT:
        quote.status = SalesQuote.Status.SENT
        quote.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Quote {quote.number} marked as sent.')
    else:
        messages.error(request, 'Only draft quotes can be sent.')
    return redirect('sales:quote_detail', pk=quote.pk)


@login_required
@require_POST
@roles_required('sales', 'accountant')
def quote_accept(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote, pk=pk, company=company)
    if quote.status in (SalesQuote.Status.SENT, SalesQuote.Status.DRAFT):
        quote.status = SalesQuote.Status.ACCEPTED
        quote.accepted_at = timezone.now()
        quote.save(update_fields=['status', 'accepted_at', 'updated_at'])
        messages.success(request, f'Quote {quote.number} accepted.')
    else:
        messages.error(request, 'This quote cannot be accepted.')
    return redirect('sales:quote_detail', pk=quote.pk)


@login_required
@require_POST
@roles_required('sales', 'accountant')
def quote_reject(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote, pk=pk, company=company)
    if quote.status in (SalesQuote.Status.SENT, SalesQuote.Status.DRAFT):
        quote.status = SalesQuote.Status.REJECTED
        quote.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Quote {quote.number} rejected.')
    else:
        messages.error(request, 'This quote cannot be rejected.')
    return redirect('sales:quote_detail', pk=quote.pk)


@login_required
@require_POST
@roles_required('sales', 'accountant')
def quote_convert_to_order(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote, pk=pk, company=company)
    if quote.status != SalesQuote.Status.ACCEPTED:
        messages.error(request, 'Only accepted quotes can be converted.')
        return redirect('sales:quote_detail', pk=quote.pk)
    order = SalesOrder.objects.create(
        company=company, number=sal.next_number(company, 'SO'),
        customer=quote.customer, warehouse_id=1,
        order_date=timezone.localdate(), status=SalesOrder.Status.DRAFT,
        currency=quote.currency, salesperson=quote.salesperson,
        notes=f'Converted from quote {quote.number}',
        created_by=request.user,
    )
    for line in quote.lines.all():
        SalesOrderLine.objects.create(
            order=order, product=line.product, description=line.description,
            quantity=line.quantity, price=line.price, discount_percent=line.discount_percent,
        )
    quote.converted_to_order = order
    quote.save(update_fields=['converted_to_order', 'updated_at'])
    messages.success(request, f'Quote {quote.number} converted to order {order.number}.')
    return redirect('sales:order_detail', pk=order.pk)


# ---------------------------------------------------------------------------
# Credit notes (Returned Invoices)
# ---------------------------------------------------------------------------
@login_required
def creditnote_list(request):
    company = _company(request)
    qs = CreditNote.objects.filter(company=company).select_related('customer')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/sales/creditnote_list.html', {
        'page_obj': page, 'status': status,
        'statuses': CreditNote.Status.choices,
    })


@login_required
def creditnote_detail(request, pk):
    company = _company(request)
    cn = get_object_or_404(CreditNote.objects.select_related('customer', 'original_invoice', 'currency'), pk=pk, company=company)
    return render(request, 'apps/sales/creditnote_detail.html', {'credit_note': cn})


@login_required
@roles_required('sales', 'accountant')
def creditnote_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('sales:creditnote_list')
    from apps.sales.forms import CreditNoteForm, CreditNoteLineForm
    form = CreditNoteForm(request.POST or None, company=company)
    formset = _inline_formset(CreditNote, CreditNoteLine, CreditNoteLineForm, request, None, company)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        has_lines = any(l.cleaned_data and not l.cleaned_data.get('DELETE') for l in formset.forms)
        if not has_lines:
            messages.error(request, 'Add at least one line item.')
        else:
            cn = form.save(commit=False)
            cn.number = sal.next_number(company, 'CN')
            cn.status = CreditNote.Status.DRAFT
            cn.save()
            formset.instance = cn
            formset.save()
            messages.success(request, f'Credit note {cn.number} created.')
            return redirect('sales:creditnote_detail', pk=cn.pk)
    return render(request, 'apps/sales/creditnote_form.html', {'form': form, 'formset': formset})


@login_required
@require_POST
@roles_required('sales', 'accountant')
def creditnote_post(request, pk):
    company = _company(request)
    cn = get_object_or_404(CreditNote, pk=pk, company=company)
    if cn.status == CreditNote.Status.DRAFT:
        cn.status = CreditNote.Status.POSTED
        cn.posted_at = timezone.now()
        cn.save(update_fields=['status', 'posted_at', 'updated_at'])
        messages.success(request, f'Credit note {cn.number} posted.')
    else:
        messages.error(request, 'Only draft credit notes can be posted.')
    return redirect('sales:creditnote_detail', pk=cn.pk)


# ---------------------------------------------------------------------------
# Periodic Invoices
# ---------------------------------------------------------------------------
@login_required
def periodic_list(request):
    company = _company(request)
    qs = PeriodicInvoice.objects.filter(company=company).select_related('customer')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/sales/periodic_list.html', {
        'page_obj': page, 'status': status,
        'statuses': PeriodicInvoice.Status.choices,
    })


@login_required
def periodic_detail(request, pk):
    company = _company(request)
    periodic = get_object_or_404(PeriodicInvoice.objects.select_related('customer'), pk=pk, company=company)
    return render(request, 'apps/sales/periodic_detail.html', {'periodic': periodic})


@login_required
@roles_required('sales', 'accountant')
def periodic_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('sales:periodic_list')
    from apps.sales.forms import PeriodicInvoiceForm
    form = PeriodicInvoiceForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        periodic = form.save(commit=False)
        periodic.number = sal.next_number(company, 'PER')
        periodic.status = PeriodicInvoice.Status.ACTIVE
        periodic.created_by = request.user
        periodic.save()
        messages.success(request, f'Periodic invoice {periodic.number} created.')
        return redirect('sales:periodic_detail', pk=periodic.pk)
    return render(request, 'apps/sales/periodic_form.html', {'form': form})


@login_required
@require_POST
@roles_required('sales', 'accountant')
def periodic_toggle(request, pk):
    company = _company(request)
    periodic = get_object_or_404(PeriodicInvoice, pk=pk, company=company)
    if periodic.status == PeriodicInvoice.Status.ACTIVE:
        periodic.status = PeriodicInvoice.Status.PAUSED
        messages.success(request, f'Periodic invoice {periodic.number} paused.')
    else:
        periodic.status = PeriodicInvoice.Status.ACTIVE
        messages.success(request, f'Periodic invoice {periodic.number} activated.')
    periodic.save(update_fields=['status', 'updated_at'])
    return redirect('sales:periodic_detail', pk=periodic.pk)


# ---------------------------------------------------------------------------
# Sales Settings
# ---------------------------------------------------------------------------
@login_required
@roles_required('sales', 'accountant')
def sales_settings(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('reports:dashboard')
    settings_obj, _ = SalesSettings.objects.get_or_create(company=company)
    from apps.sales.forms import SalesSettingsForm
    form = SalesSettingsForm(request.POST or None, instance=settings_obj, company=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Sales settings saved.')
        return redirect('sales:sales_settings')
    return render(request, 'apps/sales/sales_settings.html', {'form': form})


# ---------------------------------------------------------------------------
# Customer Payments (list)
# ---------------------------------------------------------------------------
@login_required
def payment_list(request):
    company = _company(request)
    from apps.sales.models import CustomerPayment
    qs = CustomerPayment.objects.filter(company=company).select_related('customer')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/sales/payment_list.html', {
        'page_obj': page, 'status': status,
        'statuses': CustomerPayment.Status.choices,
    })


# ---------------------------------------------------------------------------
# Billing Management (overview)
# ---------------------------------------------------------------------------
@login_required
def invoice_pdf(request, pk):
    company = _company(request)
    invoice = get_object_or_404(SalesInvoice.objects.select_related('customer', 'order', 'currency', 'tax'), pk=pk, company=company)
    from apps.core.pdf import render_to_pdf
    from apps.core.services import generate_zatca_qr

    # Compute tax amount for QR
    lines = invoice.lines.all()
    tax_amt = Decimal('0.00')
    for l in lines:
        if getattr(l, 'tax', None):
            tax_amt += l.line_total * (l.tax.rate / Decimal('100.00'))

    qr_data_uri = generate_zatca_qr(
        seller_name=company.name if company else 'ERP',
        tax_no=company.tax_id if company else '',
        timestamp_iso=f'{invoice.invoice_date}T12:00:00Z',
        total_amount=invoice.total,
        tax_amount=tax_amt
    )

    template_map = {
        'modern': 'pdf/invoice_modern.html',
        'classic': 'pdf/invoice_classic.html',
        'pos': 'pdf/invoice_pos.html',
    }
    template_name = template_map.get(getattr(invoice, 'template_design', ''), 'pdf/invoice.html')

    return render_to_pdf(template_name, {
        'invoice': invoice, 'company': company, 'qr_data_uri': qr_data_uri,
    }, filename=f'{invoice.number}.pdf')


@login_required
@require_POST
@roles_required('sales', 'accountant')
def invoice_send_email(request, pk):
    company = _company(request)
    invoice = get_object_or_404(SalesInvoice.objects.select_related('customer'), pk=pk, company=company)
    if not invoice.customer.email:
        messages.error(request, f'Customer {invoice.customer.name} has no email address.')
        return redirect('sales:invoice_detail', pk=invoice.pk)
    from apps.core.email import send_invoice_email
    send_invoice_email(invoice)
    messages.success(request, f'Invoice {invoice.number} emailed to {invoice.customer.email}.')
    return redirect('sales:invoice_detail', pk=invoice.pk)


@login_required
def customer_export(request):
    company = _company(request)
    fmt = request.GET.get('format', 'csv')
    fields = ['name', 'email', 'phone', 'tax_id', 'is_active']
    qs = Customer.objects.filter(company=company).order_by('name')
    from apps.core.export import export_to_csv, export_to_excel
    if fmt == 'xlsx':
        return export_to_excel(qs, fields, 'customers.xlsx')
    return export_to_csv(qs, fields, 'customers.csv')


@login_required
@roles_required('sales', 'accountant')
def customer_import(request):
    company = _company(request)
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Please upload a file.')
            return redirect('sales:customer_list')
        from apps.core.export import import_customers_from_file
        count, errors = import_customers_from_file(file, company, user=request.user)
        if errors:
            for e in errors[:5]:
                messages.warning(request, e)
        messages.success(request, f'{count} customer(s) imported successfully.')
        return redirect('sales:customer_list')
    return render(request, 'apps/sales/customer_import.html')


@login_required
def customer_statement(request, pk):
    company = _company(request)
    customer = get_object_or_404(Customer, pk=pk, company=company)
    start_date = request.GET.get('start', '')
    end_date = request.GET.get('end', '')

    invoices = customer.ar_invoices.filter(company=company).select_related('currency')
    payments = customer.payments.filter(company=company)

    if start_date:
        from datetime import date
        invoices = invoices.filter(invoice_date__gte=start_date)
        payments = payments.filter(date__gte=start_date)
    if end_date:
        from datetime import date
        invoices = invoices.filter(invoice_date__lte=end_date)
        payments = payments.filter(date__lte=end_date)

    lines = []
    for inv in invoices:
        lines.append({'date': inv.invoice_date, 'type': 'Invoice', 'reference': inv.number, 'debit': inv.total, 'credit': Decimal('0.00'), 'balance': None})
    for pmt in payments:
        lines.append({'date': pmt.date, 'type': 'Payment', 'reference': pmt.number, 'debit': Decimal('0.00'), 'credit': pmt.amount, 'balance': None})

    lines.sort(key=lambda x: x['date'] or timezone.localdate())

    running = Decimal('0.00')
    for line in lines:
        running = running + line['debit'] - line['credit']
        line['balance'] = running

    return render(request, 'apps/sales/customer_statement.html', {
        'customer': customer, 'lines': lines, 'start_date': start_date, 'end_date': end_date,
    })


@login_required
def quote_pdf(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote.objects.select_related('customer', 'currency', 'salesperson'), pk=pk, company=company)
    from apps.core.pdf import render_to_pdf
    return render_to_pdf('pdf/quote.html', {
        'quote': quote, 'company': company,
    }, filename=f'{quote.number}.pdf')


@login_required
def billing_management(request):
    company = _company(request)
    from decimal import Decimal
    invoices = SalesInvoice.objects.filter(company=company).select_related('customer')
    total_invoiced = sum(i.total for i in invoices)
    total_paid = sum(i.paid_total for i in invoices)
    open_count = invoices.filter(status__in=['draft', 'posted']).count()
    paid_count = invoices.filter(status='paid').count()
    overdue_invoices = [i for i in invoices.filter(status='posted') if i.due_date and i.due_date < timezone.localdate()]
    recent_invoices = invoices[:10]
    return render(request, 'apps/sales/billing_management.html', {
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'total_outstanding': total_invoiced - total_paid,
        'open_count': open_count,
        'paid_count': paid_count,
        'overdue_count': len(overdue_invoices),
        'overdue_invoices': overdue_invoices,
        'recent_invoices': recent_invoices,
    })


# ---------------------------------------------------------------------------
# Edit / Delete for Orders, Quotes, Credit Notes, Payments
# ---------------------------------------------------------------------------

@login_required
@roles_required('sales', 'admin')
def order_edit(request, pk):
    company = _company(request)
    order = get_object_or_404(SalesOrder, pk=pk, company=company)
    if order.status != 'draft':
        messages.error(request, 'Only draft orders can be edited.')
        return redirect('sales:order_detail', pk=pk)
    from apps.sales.forms import OrderForm
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order, company=company)
        if form.is_valid():
            form.save(company=company)
            messages.success(request, f'Order {order.number} updated.')
            return redirect('sales:order_detail', pk=pk)
    else:
        form = OrderForm(instance=order, company=company)
    return render(request, 'apps/sales/order_form.html', {'form': form, 'order': order})


@login_required
@roles_required('sales', 'admin')
@require_POST
def order_delete(request, pk):
    company = _company(request)
    order = get_object_or_404(SalesOrder, pk=pk, company=company)
    if order.status != 'draft':
        messages.error(request, 'Only draft orders can be deleted.')
        return redirect('sales:order_detail', pk=pk)
    order.delete()
    messages.success(request, f'Order deleted.')
    return redirect('sales:order_list')


@login_required
@roles_required('sales', 'admin')
def quote_edit(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote, pk=pk, company=company)
    if quote.status != 'draft':
        messages.error(request, 'Only draft quotes can be edited.')
        return redirect('sales:quote_detail', pk=pk)
    from apps.sales.forms import QuoteForm
    if request.method == 'POST':
        form = QuoteForm(request.POST, instance=quote, company=company)
        if form.is_valid():
            form.save(company=company)
            messages.success(request, f'Quote {quote.number} updated.')
            return redirect('sales:quote_detail', pk=pk)
    else:
        form = QuoteForm(instance=quote, company=company)
    return render(request, 'apps/sales/quote_form.html', {'form': form, 'quote': quote})


@login_required
@roles_required('sales', 'admin')
@require_POST
def quote_delete(request, pk):
    company = _company(request)
    quote = get_object_or_404(SalesQuote, pk=pk, company=company)
    if quote.status != 'draft':
        messages.error(request, 'Only draft quotes can be deleted.')
        return redirect('sales:quote_detail', pk=pk)
    quote.delete()
    messages.success(request, f'Quote deleted.')
    return redirect('sales:quote_list')


@login_required
@roles_required('sales', 'admin')
@require_POST
def creditnote_delete(request, pk):
    company = _company(request)
    cn = get_object_or_404(CreditNote, pk=pk, company=company)
    if cn.status != 'draft':
        messages.error(request, 'Only draft credit notes can be deleted.')
        return redirect('sales:creditnote_detail', pk=pk)
    cn.delete()
    messages.success(request, f'Credit note deleted.')
    return redirect('sales:creditnote_list')


@login_required
@roles_required('sales', 'admin')
@require_POST
def payment_delete(request, pk):
    company = _company(request)
    payment = get_object_or_404(CustomerPayment, pk=pk, company=company)
    payment.delete()
    messages.success(request, f'Payment deleted.')
    return redirect('sales:payment_list')