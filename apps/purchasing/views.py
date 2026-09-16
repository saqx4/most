from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import roles_required
from apps.core.services import get_company
from apps.purchasing import services as pur
from apps.purchasing.forms import (BillForm, BillLineForm, POForm, POLineForm,
                                    SupplierForm, SupplierPaymentForm)
from apps.purchasing.models import (GoodsReceipt, GoodsReceiptLine,
                                     PurchaseOrder, PurchaseOrderLine,
                                     Supplier, SupplierBill, SupplierBillLine,
                                     SupplierPayment)


def _company(request):
    return get_company(request.user)


# ─────────────────────────────── Dashboard ───────────────────────────────────

@login_required
def dashboard(request):
    company = _company(request)
    total_suppliers = Supplier.objects.filter(company=company, is_active=True).count()
    open_pos = PurchaseOrder.objects.filter(company=company, status__in=['draft', 'confirmed']).count()
    open_bills = SupplierBill.objects.filter(company=company, status__in=['draft', 'posted'])
    total_payable = sum(b.total - b.paid_total for b in open_bills)
    recent_pos = PurchaseOrder.objects.filter(company=company).select_related('supplier')[:8]
    recent_bills = SupplierBill.objects.filter(company=company).select_related('supplier')[:8]
    return render(request, 'apps/purchasing/dashboard.html', {
        'total_suppliers': total_suppliers,
        'open_pos': open_pos,
        'total_payable': total_payable,
        'recent_pos': recent_pos,
        'recent_bills': recent_bills,
    })


# ──────────────────────────────── Suppliers ──────────────────────────────────

@login_required
def supplier_list(request):
    company = _company(request)
    q = request.GET.get('q', '').strip()
    qs = Supplier.objects.filter(company=company)
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/purchasing/supplier_list.html', {'page_obj': page, 'q': q})


@login_required
def supplier_detail(request, pk):
    company = _company(request)
    supplier = get_object_or_404(Supplier, pk=pk, company=company)
    pos = supplier.purchase_orders.all()[:10]
    bills = supplier.bills.all()[:10]
    payments = supplier.payments.all()[:10]
    balance = sum(b.total - b.paid_total for b in supplier.bills.filter(status__in=['draft', 'posted']))
    return render(request, 'apps/purchasing/supplier_detail.html', {
        'supplier': supplier, 'pos': pos, 'bills': bills,
        'payments': payments, 'balance': balance,
    })


@login_required
@roles_required('purchasing', 'admin')
def supplier_create(request):
    company = _company(request)
    form = SupplierForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        supplier = form.save(company=company)
        messages.success(request, f'Supplier "{supplier.name}" created.')
        return redirect('purchasing:supplier_detail', pk=supplier.pk)
    return render(request, 'apps/purchasing/supplier_form.html', {'form': form, 'title': 'New Supplier'})


@login_required
@roles_required('purchasing', 'admin')
def supplier_edit(request, pk):
    company = _company(request)
    supplier = get_object_or_404(Supplier, pk=pk, company=company)
    form = SupplierForm(request.POST or None, instance=supplier, company=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Supplier updated.')
        return redirect('purchasing:supplier_detail', pk=supplier.pk)
    return render(request, 'apps/purchasing/supplier_form.html', {'form': form, 'title': 'Edit Supplier', 'supplier': supplier})


@login_required
@require_POST
@roles_required('purchasing', 'admin')
def supplier_delete(request, pk):
    company = _company(request)
    supplier = get_object_or_404(Supplier, pk=pk, company=company)
    name = supplier.name
    supplier.delete()
    messages.success(request, f'Supplier "{name}" deleted.')
    return redirect('purchasing:supplier_list')


# ─────────────────────────────── Purchase Orders ─────────────────────────────

@login_required
def po_list(request):
    company = _company(request)
    status = request.GET.get('status', '')
    qs = PurchaseOrder.objects.filter(company=company).select_related('supplier')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/purchasing/po_list.html', {
        'page_obj': page, 'status': status,
        'status_choices': [('draft','Draft'),('confirmed','Confirmed'),('partial','Partial'),('received','Received'),('cancelled','Cancelled')],
    })


@login_required
def po_detail(request, pk):
    company = _company(request)
    po = get_object_or_404(PurchaseOrder.objects.select_related('supplier', 'tax', 'currency'), pk=pk, company=company)
    lines = po.lines.select_related('product', 'tax')
    receipts = po.goods_receipts.all()
    bills = po.bills.all()
    return render(request, 'apps/purchasing/po_detail.html', {
        'po': po, 'lines': lines, 'receipts': receipts, 'bills': bills,
    })


@login_required
@roles_required('purchasing', 'admin')
def po_create(request):
    company = _company(request)
    LineFormSet = inlineformset_factory(PurchaseOrder, PurchaseOrderLine, form=POLineForm,
                                        extra=2, can_delete=True, min_num=1, validate_min=True)
    if request.method == 'POST':
        form = POForm(request.POST, company=company)
        formset = LineFormSet(request.POST, form_kwargs={'company': company})
        if form.is_valid() and formset.is_valid():
            po = form.save(company=company, user=request.user)
            po.number = pur.next_number(company, 'PO')
            po.save(update_fields=['number'])
            formset.instance = po
            formset.save()
            messages.success(request, f'Purchase Order {po.number} created.')
            return redirect('purchasing:po_detail', pk=po.pk)
    else:
        form = POForm(company=company)
        formset = LineFormSet(form_kwargs={'company': company})
    return render(request, 'apps/purchasing/po_form.html', {
        'form': form, 'formset': formset, 'title': 'New Purchase Order',
    })


@login_required
@roles_required('purchasing', 'admin')
def po_confirm(request, pk):
    company = _company(request)
    po = get_object_or_404(PurchaseOrder, pk=pk, company=company)
    if po.status != 'draft':
        messages.error(request, 'Only draft orders can be confirmed.')
        return redirect('purchasing:po_detail', pk=po.pk)
    po.status = 'confirmed'
    po.confirmed_by = request.user
    po.confirmed_at = timezone.now()
    po.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])
    messages.success(request, f'{po.number} confirmed.')
    return redirect('purchasing:po_detail', pk=po.pk)


@login_required
@roles_required('purchasing', 'admin')
def po_cancel(request, pk):
    company = _company(request)
    po = get_object_or_404(PurchaseOrder, pk=pk, company=company)
    if po.status in ('received', 'closed'):
        messages.error(request, 'Cannot cancel a received or closed order.')
        return redirect('purchasing:po_detail', pk=po.pk)
    po.status = 'cancelled'
    po.save(update_fields=['status'])
    messages.success(request, f'{po.number} cancelled.')
    return redirect('purchasing:po_detail', pk=po.pk)


@login_required
def po_pdf(request, pk):
    company = _company(request)
    po = get_object_or_404(PurchaseOrder.objects.select_related('supplier', 'tax', 'currency'), pk=pk, company=company)
    from apps.core.pdf import render_to_pdf
    return render_to_pdf('pdf/purchase_order.html', {
        'po': po, 'company': company,
    }, filename=f'{po.number}.pdf')


# ──────────────────────────────── Goods Receipts ─────────────────────────────

@login_required
@roles_required('purchasing', 'warehouse', 'admin')
def receipt_create(request, po_pk):
    company = _company(request)
    po = get_object_or_404(PurchaseOrder, pk=po_pk, company=company)
    LineFormSet = inlineformset_factory(GoodsReceipt, GoodsReceiptLine,
                                        fields=['product', 'quantity', 'unit_cost'],
                                        extra=len(list(po.lines.all())), can_delete=False, min_num=1)
    if request.method == 'POST':
        receipt = GoodsReceipt(company=company, order=po, supplier=po.supplier,
                               created_by=request.user)
        receipt.number = pur.next_number(company, 'GR')
        receipt.save()
        formset = LineFormSet(request.POST, instance=receipt)
        if formset.is_valid():
            formset.save()
            try:
                pur.post_goods_receipt(receipt, user=request.user)
                messages.success(request, f'Goods Receipt {receipt.number} posted.')
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('purchasing:po_detail', pk=po.pk)
        else:
            receipt.delete()
    else:
        formset = LineFormSet()
    return render(request, 'apps/purchasing/receipt_form.html', {
        'po': po, 'formset': formset,
    })


# ─────────────────────────────── Supplier Bills ──────────────────────────────

@login_required
def bill_list(request):
    company = _company(request)
    status = request.GET.get('status', '')
    qs = SupplierBill.objects.filter(company=company).select_related('supplier')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/purchasing/bill_list.html', {
        'page_obj': page, 'status': status,
        'status_choices': [('draft','Draft'),('posted','Posted'),('paid','Paid'),('void','Void')],
    })


@login_required
def bill_detail(request, pk):
    company = _company(request)
    bill = get_object_or_404(SupplierBill.objects.select_related('supplier', 'order', 'tax', 'currency'),
                             pk=pk, company=company)
    lines = bill.lines.select_related('product', 'tax')
    allocations = bill.payments_allocations.select_related('payment')
    return render(request, 'apps/purchasing/bill_detail.html', {
        'bill': bill, 'lines': lines, 'allocations': allocations,
    })


@login_required
@roles_required('purchasing', 'accountant', 'admin')
def bill_create(request):
    company = _company(request)
    LineFormSet = inlineformset_factory(SupplierBill, SupplierBillLine, form=BillLineForm,
                                        extra=2, can_delete=True, min_num=1, validate_min=True)
    if request.method == 'POST':
        form = BillForm(request.POST, company=company)
        formset = LineFormSet(request.POST, form_kwargs={'company': company})
        if form.is_valid() and formset.is_valid():
            bill = form.save(company=company, user=request.user)
            bill.number = pur.next_number(company, 'BILL')
            bill.save(update_fields=['number'])
            formset.instance = bill
            formset.save()
            messages.success(request, f'Bill {bill.number} created.')
            return redirect('purchasing:bill_detail', pk=bill.pk)
    else:
        form = BillForm(company=company)
        formset = LineFormSet(form_kwargs={'company': company})
    return render(request, 'apps/purchasing/bill_form.html', {
        'form': form, 'formset': formset, 'title': 'New Supplier Bill',
    })


@login_required
@roles_required('purchasing', 'accountant', 'admin')
def bill_post(request, pk):
    company = _company(request)
    bill = get_object_or_404(SupplierBill, pk=pk, company=company)
    try:
        pur.post_supplier_bill(bill, user=request.user)
        messages.success(request, f'Bill {bill.number} posted.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('purchasing:bill_detail', pk=bill.pk)


# ──────────────────────────────── Supplier Payments ──────────────────────────

@login_required
def payment_list(request):
    company = _company(request)
    qs = SupplierPayment.objects.filter(company=company).select_related('supplier')
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/purchasing/payment_list.html', {'page_obj': page})


@login_required
@roles_required('purchasing', 'accountant', 'admin')
def payment_create(request):
    company = _company(request)
    form = SupplierPaymentForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        payment = form.save(company=company, user=request.user)
        payment.number = pur.next_number(company, 'SPAY')
        payment.save(update_fields=['number'])
        try:
            pur.post_supplier_payment(payment, user=request.user)
            messages.success(request, f'Payment {payment.number} posted.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('purchasing:payment_list')
    return render(request, 'apps/purchasing/payment_form.html', {'form': form, 'title': 'New Supplier Payment'})


# ---------------------------------------------------------------------------
# Edit / Delete for Bills and Payments
# ---------------------------------------------------------------------------

@login_required
@roles_required('purchasing', 'admin')
def bill_edit(request, pk):
    company = _company(request)
    bill = get_object_or_404(SupplierBill, pk=pk, company=company)
    if bill.status != 'draft':
        messages.error(request, 'Only draft bills can be edited.')
        return redirect('purchasing:bill_detail', pk=pk)
    from apps.purchasing.forms import BillForm
    if request.method == 'POST':
        form = BillForm(request.POST, instance=bill, company=company)
        if form.is_valid():
            form.save(company=company)
            messages.success(request, f'Bill {bill.number} updated.')
            return redirect('purchasing:bill_detail', pk=pk)
    else:
        form = BillForm(instance=bill, company=company)
    return render(request, 'apps/purchasing/bill_form.html', {'form': form, 'bill': bill, 'title': f'Edit Bill: {bill.number}'})


@login_required
@roles_required('purchasing', 'admin')
@require_POST
def bill_delete(request, pk):
    company = _company(request)
    bill = get_object_or_404(SupplierBill, pk=pk, company=company)
    if bill.status != 'draft':
        messages.error(request, 'Only draft bills can be deleted.')
        return redirect('purchasing:bill_detail', pk=pk)
    bill.delete()
    messages.success(request, f'Bill deleted.')
    return redirect('purchasing:bill_list')


@login_required
@roles_required('purchasing', 'admin')
@require_POST
def payment_delete(request, pk):
    company = _company(request)
    payment = get_object_or_404(SupplierPayment, pk=pk, company=company)
    payment.delete()
    messages.success(request, f'Supplier payment deleted.')
    return redirect('purchasing:payment_list')
