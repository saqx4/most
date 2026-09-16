from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.services import get_sequence_next, log_audit

ZERO = Decimal('0.00')


def next_number(company, prefix, padding=4):
    seq_name = f'{prefix}{company.pk}'
    return get_sequence_next(seq_name, prefix=prefix, padding=padding)


def _resolve_account(company, codes, types):
    from apps.accounting.models import Account
    for code in codes:
        acct = Account.objects.filter(company=company, code=code, is_active=True).first()
        if acct:
            return acct
    return Account.objects.filter(company=company, type__in=types, is_active=True).order_by('code').first()


def confirm_purchase_order(order, user=None):
    from apps.purchasing.models import PurchaseOrder
    if order.status != PurchaseOrder.status.field.choices[0][0]:  # draft
        pass
    order.status = 'confirmed'
    order.confirmed_by = user
    order.confirmed_at = timezone.now()
    order.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])
    log_audit(user, 'confirm', 'PurchaseOrder', order.pk, f'Confirmed {order.number}')
    return order


def post_goods_receipt(receipt, user=None):
    from apps.purchasing.models import GoodsReceipt
    from apps.inventory.services import apply_stock_movement
    from apps.inventory.models import StockMovement

    if receipt.status == GoodsReceipt.Status.POSTED:
        return receipt
    if receipt.status == GoodsReceipt.Status.CANCELLED:
        raise ValueError('Cancelled receipt cannot be posted.')

    with transaction.atomic():
        for line in receipt.lines.select_related('product'):
            apply_stock_movement(
                receipt.company,
                product=line.product,
                warehouse=receipt.warehouse,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                movement_type=StockMovement.MovementType.PO_IN,
                reference_type='GOODS_RECEIPT',
                reference_id=receipt.pk,
                reference_number=receipt.number,
                notes=f'GR {receipt.number}',
                user=user,
            )
            # Update quantity_received on linked PO line
            if line.order_line_id:
                line.order_line.quantity_received = (
                    line.order_line.quantity_received + line.quantity
                )
                line.order_line.save(update_fields=['quantity_received', 'updated_at'])

        # Update PO status
        if receipt.order:
            order = receipt.order
            lines = list(order.lines.all())
            all_received = all(l.quantity_received >= l.quantity for l in lines)
            any_received = any(l.quantity_received > 0 for l in lines)
            if all_received:
                order.status = 'received'
            elif any_received:
                order.status = 'partial'
            order.save(update_fields=['status'])

        receipt.status = GoodsReceipt.Status.POSTED
        receipt.posted_at = timezone.now()
        receipt.save(update_fields=['status', 'posted_at'])

    log_audit(user, 'post', 'GoodsReceipt', receipt.pk, f'Posted {receipt.number}')
    return receipt


def post_supplier_bill(bill, user=None):
    from apps.accounting.models import Account, JournalEntry, JournalLine
    from apps.purchasing.models import SupplierBill

    if bill.status != SupplierBill.Status.DRAFT:
        raise ValueError('Only draft bills can be posted.')

    company = bill.company
    ap = (bill.supplier.ap_account if bill.supplier.ap_account_id
          else _resolve_account(company, ['2000'], ['liability']))
    if ap is None:
        raise ValueError('No Accounts Payable account configured (expect code 2000).')
    expense_default = _resolve_account(company, ['5000', '6000'], ['expense'])
    if expense_default is None:
        raise ValueError('No expense account configured.')
    tax_account = _resolve_account(company, ['2100'], ['liability'])

    from decimal import Decimal
    ZERO = Decimal('0.00')
    lines = list(bill.lines.select_related('product', 'tax'))
    expense_by_account = {}
    total_net = ZERO
    total_tax = ZERO

    for line in lines:
        net = line.subtotal()
        exp = (line.product.expense_account if line.product.expense_account_id else expense_default)
        expense_by_account.setdefault(exp.pk, [exp, ZERO])[1] += net
        total_net += net
        if line.tax:
            total_tax += net * (line.tax.rate / Decimal('100.00'))

    grand = total_net + total_tax

    with transaction.atomic():
        from django.contrib.contenttypes.models import ContentType
        entry = JournalEntry.objects.create(
            company=company,
            entry_number=next_number(company, 'JE'),
            date=bill.bill_date,
            memo=f'Supplier bill {bill.number} – {bill.supplier.name}',
            reference=bill.number,
            status=JournalEntry.Status.DRAFT,
            created_by=user,
        )
        ct = ContentType.objects.get_for_model(bill.supplier._meta.model)
        # Debit expenses
        for exp, amount in expense_by_account.values():
            JournalLine.objects.create(
                entry=entry, account=exp, debit=amount, credit=ZERO,
                description=f'Purchase expense {bill.number}',
                partner_type=ct, partner_id=bill.supplier.pk,
            )
        # Debit tax
        if total_tax and tax_account:
            JournalLine.objects.create(
                entry=entry, account=tax_account, debit=total_tax, credit=ZERO,
                description=f'Purchase tax {bill.number}',
            )
        # Credit AP
        JournalLine.objects.create(
            entry=entry, account=ap, debit=ZERO, credit=grand,
            description=f'AP – {bill.supplier.name} {bill.number}',
            partner_type=ct, partner_id=bill.supplier.pk,
        )
        # Post journal entry
        entry.status = JournalEntry.Status.POSTED
        entry.save(update_fields=['status', 'updated_at'])

        bill.status = SupplierBill.Status.POSTED
        bill.posted_at = timezone.now()
        bill.save(update_fields=['status', 'posted_at'])

    log_audit(user, 'post', 'SupplierBill', bill.pk, f'Posted {bill.number}')
    return bill


def post_supplier_payment(payment, user=None):
    from apps.accounting.models import JournalEntry, JournalLine
    from apps.purchasing.models import APPaymentAllocation, SupplierBill, SupplierPayment

    company = payment.company
    cash = _resolve_account(company, ['1000'], ['asset'])
    if cash is None:
        raise ValueError('No bank/cash account configured (expect code 1000).')
    ap = (payment.supplier.ap_account if payment.supplier.ap_account_id
          else _resolve_account(company, ['2000'], ['liability']))
    if ap is None:
        raise ValueError('No Accounts Payable account configured (expect code 2000).')

    open_bills = list(
        SupplierBill.objects.filter(
            company=company, supplier=payment.supplier, status=SupplierBill.Status.POSTED
        ).order_by('bill_date', 'id')
    )

    allocations = []
    remaining = payment.amount
    ZERO = Decimal('0.00')

    with transaction.atomic():
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(payment.supplier._meta.model)
        entry = JournalEntry.objects.create(
            company=company,
            entry_number=next_number(company, 'JE'),
            date=payment.date,
            memo=f'Supplier payment {payment.number} – {payment.supplier.name}',
            reference=payment.number,
            status=JournalEntry.Status.DRAFT,
            created_by=user,
        )
        paid_total = ZERO
        for bill in open_bills:
            if remaining <= ZERO:
                break
            balance = bill.total - bill.paid_total
            if balance <= ZERO:
                continue
            alloc = min(remaining, balance)
            APPaymentAllocation.objects.create(payment=payment, bill=bill, allocated=alloc)
            allocations.append((bill, alloc))
            paid_total += alloc
            remaining -= alloc
            if bill.total - bill.paid_total - alloc <= ZERO:
                bill.status = SupplierBill.Status.PAID
                bill.save(update_fields=['status'])

        if not allocations:
            paid_total = payment.amount

        # Debit AP, Credit cash
        JournalLine.objects.create(
            entry=entry, account=ap, debit=paid_total, credit=ZERO,
            description=f'Supplier payment {payment.number}',
            partner_type=ct, partner_id=payment.supplier.pk,
        )
        JournalLine.objects.create(
            entry=entry, account=cash, debit=ZERO, credit=paid_total,
            description=f'Supplier payment {payment.number}',
            partner_type=ct, partner_id=payment.supplier.pk,
        )
        entry.status = JournalEntry.Status.POSTED
        entry.save(update_fields=['status', 'updated_at'])

        payment.status = SupplierPayment.Status.RECEIVED
        payment.posted_at = timezone.now()
        payment.save(update_fields=['status', 'posted_at'])

    log_audit(user, 'post', 'SupplierPayment', payment.pk, f'Posted {payment.number}')
    return allocations
