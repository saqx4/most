from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalLine
from apps.core.services import get_sequence_next, log_audit

ZERO = Decimal('0.00')


def next_number(company, prefix, padding=4):
    from apps.sales.models import SalesSettings
    settings = SalesSettings.objects.filter(company=company).first()
    pad = padding
    fmt = 'prefix_num'
    if settings:
        pad = settings.number_padding or padding
        fmt = settings.number_format if hasattr(settings, 'number_format') else settings.numbering_format
        if prefix == 'INV' and settings.invoice_prefix:
            prefix = settings.invoice_prefix
        elif prefix == 'QOT' and settings.quote_prefix:
            prefix = settings.quote_prefix
        elif prefix == 'CN' and settings.credit_note_prefix:
            prefix = settings.credit_note_prefix
        elif prefix == 'SO' and settings.order_prefix:
            prefix = settings.order_prefix
        elif prefix == 'RCPT' and settings.receipt_prefix:
            prefix = settings.receipt_prefix

    today = timezone.localdate()
    seq_name = f'{prefix}_{company.pk}'
    if settings and getattr(settings, 'reset_sequence_yearly', False):
        seq_name = f'{prefix}_{company.pk}_{today.year}'

    from apps.core.models import NumberSequence
    seq, _ = NumberSequence.objects.get_or_create(
        name=seq_name, defaults={'prefix': prefix, 'padding': pad}
    )
    seq.last_number += 1
    seq.save(update_fields=['last_number', 'updated_at'])

    num_part = f'{seq.last_number:0{pad}d}'
    if fmt == 'prefix_year_num':
        return f'{prefix}-{today.year}-{num_part}'
    elif fmt == 'prefix_month_num':
        return f'{prefix}-{today.year}-{today.month:02d}-{num_part}'
    return f'{prefix}-{num_part}'


def document_total(lines, invoice=None):
    from apps.sales.models import line_amount
    subtotal = ZERO
    tax_total = ZERO
    for line in lines:
        gross = line.price * line.quantity
        if getattr(line, 'discount_type', 'percent') == 'fixed':
            disc = getattr(line, 'discount_amount', ZERO) or ZERO
        else:
            disc = gross * ((getattr(line, 'discount_percent', ZERO) or ZERO) / Decimal('100.00'))
        net = max(ZERO, gross - disc)
        subtotal += net
        if getattr(line, 'tax', None):
            tax_total += net * (line.tax.rate / Decimal('100.00'))
        if getattr(line, 'tax2', None):
            tax_total += net * (line.tax2.rate / Decimal('100.00'))

    total = subtotal + tax_total

    if invoice:
        # Global discount
        g_disc = getattr(invoice, 'global_discount_value', ZERO) or ZERO
        if getattr(invoice, 'global_discount_type', 'fixed') == 'percent':
            total -= subtotal * (g_disc / Decimal('100.00'))
        else:
            total -= g_disc

        # Shipping
        shipping = getattr(invoice, 'shipping_amount', ZERO) or ZERO
        total += shipping

        # Adjustment
        adjustment = getattr(invoice, 'adjustment_value', ZERO) or ZERO
        total += adjustment

    return max(ZERO, total)


def _resolve_account(company, codes, types):
    if company is None:
        return None
    for code in codes:
        account = Account.objects.filter(company=company, code=code, is_active=True).order_by('code').first()
        if account:
            return account
    return Account.objects.filter(company=company, type__in=types, is_active=True).order_by('code').first()


def _post_journal(entry, user=None):
    if entry.debit_total != entry.credit_total:
        raise ValueError('Sales journal entry is not balanced.')
    entry.status = JournalEntry.Status.POSTED
    entry.save(update_fields=['status', 'updated_at'])
    log_audit(user, 'post', 'JournalEntry', entry.pk, f'Posted sales entry {entry.entry_number}')
    return entry


def confirm_order(order, user=None):
    from apps.sales.models import SalesOrder

    if order.company is None:
        raise ValueError('Order has no company; cannot post a journal entry.')
    if order.status != SalesOrder.Status.DRAFT:
        raise ValueError('Only draft orders can be confirmed.')
    company = order.company
    ar = order.customer.ar_account or _resolve_account(company, ['1100'], ['asset'])
    if ar is None:
        raise ValueError('No Accounts Receivable account configured (expect code 1100).')
    income_default = _resolve_account(company, ['4000'], ['income'])
    if income_default is None:
        raise ValueError('No Income account configured (expect code 4000).')
    tax_account = _resolve_account(company, ['2100'], ['liability'])

    from apps.sales.models import line_amount
    line_rows = list(order.lines.select_related('product', 'tax'))
    income_by_account = {}
    total_net = ZERO
    total_tax = ZERO
    for line in line_rows:
        net = line_amount(line.price, line.quantity, line.discount_percent)
        inc = line.product.income_account or income_default
        income_by_account.setdefault(inc.pk, [inc, ZERO])[1] += net
        total_net += net
        if line.tax:
            tax_amt = net * (line.tax.rate / Decimal('100.00'))
            total_tax += tax_amt
    grand = total_net + total_tax

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, entry_number=next_number(company, 'JE'),
            date=order.order_date, memo=f'Sales order {order.number} - {order.customer.name}',
            reference=order.number, status=JournalEntry.Status.DRAFT,
            created_by=user,
        )
        ct = ContentType.objects.get_for_model(order.customer._meta.model)
        JournalLine.objects.create(
            entry=entry, account=ar, debit=grand, credit=ZERO,
            description=f'Sale {order.number}',
            partner_type=ct, partner_id=order.customer.pk,
        )
        for inc, amount in income_by_account.values():
            JournalLine.objects.create(
                entry=entry, account=inc, debit=ZERO, credit=amount,
                description=f'Sale revenue {order.number}',
                partner_type=ct, partner_id=order.customer.pk,
            )
        if total_tax and tax_account:
            JournalLine.objects.create(
                entry=entry, account=tax_account, debit=ZERO, credit=total_tax,
                description=f'Sales tax {order.number}',
            )
        _post_journal(entry, user=user)
        order.status = SalesOrder.Status.CONFIRMED
        order.confirmed_at = timezone.now()
        order.save()
        log_audit(user, 'confirm', 'SalesOrder', order.pk, f'Confirmed {order.number} (JE {entry.entry_number})')
    return order


def pay_invoice(invoice, user=None, date=None):
    """Mark an invoice paid: books cash against AR and allocates a received payment."""
    from apps.sales.models import ARPaymentAllocation, CustomerPayment, SalesInvoice

    if invoice.status == SalesInvoice.Status.PAID:
        return invoice
    if invoice.status == SalesInvoice.Status.VOID:
        raise ValueError('A void invoice cannot be paid.')
    amount = invoice.amount_due
    if amount <= ZERO:
        raise ValueError('Invoice has nothing outstanding.')
    company = invoice.company
    cash = _resolve_account(company, ['1000'], ['asset'])
    if cash is None:
        raise ValueError('No bank/cash account configured (expect code 1000).')
    ar = invoice.customer.ar_account or _resolve_account(company, ['1100'], ['asset'])
    if ar is None:
        raise ValueError('No Accounts Receivable account configured (expect code 1100).')

    with transaction.atomic():
        new_status = SalesInvoice.Status.POSTED if invoice.status == SalesInvoice.Status.DRAFT else invoice.status
        invoice.status = SalesInvoice.Status.PAID
        invoice.posted_at = timezone.now()
        invoice.save()

        payment = CustomerPayment.objects.create(
            company=company, number=next_number(company, 'PAY'),
            customer=invoice.customer, date=date or timezone.localdate(),
            amount=amount, status=CustomerPayment.Status.RECEIVED,
            notes=f'Payment for {invoice.number}', created_by=user,
            posted_at=timezone.now(),
        )
        ARPaymentAllocation.objects.create(payment=payment, invoice=invoice, allocated=amount)

        entry = JournalEntry.objects.create(
            company=company, entry_number=next_number(company, 'JE'),
            date=date or timezone.localdate(),
            memo=f'Payment {payment.number} - {invoice.customer.name}',
            reference=payment.number, status=JournalEntry.Status.DRAFT, created_by=user,
        )
        ct = ContentType.objects.get_for_model(invoice.customer._meta.model)
        JournalLine.objects.create(
            entry=entry, account=cash, debit=amount, credit=ZERO,
            description=f'Customer payment {payment.number}',
            partner_type=ct, partner_id=invoice.customer.pk,
        )
        JournalLine.objects.create(
            entry=entry, account=ar, debit=ZERO, credit=amount,
            description=f'Receipt against {invoice.number}',
            partner_type=ct, partner_id=invoice.customer.pk,
        )
        _post_journal(entry, user=user)
        log_audit(user, 'pay', 'SalesInvoice', invoice.pk, f'Paid {invoice.number} (payment {payment.number})')
    return payment


def post_customer_payment(payment, user=None):
    """Apply a received customer payment to the oldest open invoices first."""
    from apps.sales.models import ARPaymentAllocation, SalesInvoice

    if payment.company is None:
        raise ValueError('Payment has no company.')
    company = payment.company
    cash = _resolve_account(company, ['1000'], ['asset'])
    if cash is None:
        raise ValueError('No bank/cash account configured (expect code 1000).')
    ar = payment.customer.ar_account or _resolve_account(company, ['1100'], ['asset'])
    if ar is None:
        raise ValueError('No Accounts Receivable account configured (expect code 1100).')

    open_invoices = list(
        SalesInvoice.objects.filter(company=company, customer=payment.customer, status__in=('posted',))
        .order_by('invoice_date', 'id')
    )
    if not open_invoices:
        raise ValueError('No open invoices for this customer.')

    allocations = []
    remaining = payment.amount
    ct = ContentType.objects.get_for_model(payment.customer._meta.model)
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            company=company, entry_number=next_number(company, 'JE'),
            date=payment.date, memo=f'Payment {payment.number} - {payment.customer.name}',
            reference=payment.number, status=JournalEntry.Status.DRAFT, created_by=user,
        )
        credited = ZERO
        for invoice in open_invoices:
            if remaining <= ZERO:
                break
            alloc = min(remaining, invoice.amount_due)
            if alloc <= ZERO:
                continue
            ARPaymentAllocation.objects.create(payment=payment, invoice=invoice, allocated=alloc)
            allocations.append((invoice, alloc))
            credited += alloc
            remaining -= alloc
            if invoice.amount_due - alloc <= ZERO:
                invoice.status = SalesInvoice.Status.PAID
                invoice.save()
        if not allocations:
            raise ValueError('No open invoice balances to allocate against.')
        JournalLine.objects.create(
            entry=entry, account=cash, debit=credited, credit=ZERO,
            description=f'Customer payment {payment.number}',
            partner_type=ct, partner_id=payment.customer.pk,
        )
        JournalLine.objects.create(
            entry=entry, account=ar, debit=ZERO, credit=credited,
            description=f'Customer payment {payment.number}',
            partner_type=ct, partner_id=payment.customer.pk,
        )
        _post_journal(entry, user=user)
        payment.status = 'received'
        payment.posted_at = timezone.now()
        payment.save()
    return allocations