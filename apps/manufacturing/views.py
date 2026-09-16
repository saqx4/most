from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import roles_required
from apps.core.services import get_company, get_sequence_next
from apps.manufacturing.forms import BOMForm, BOMLineForm, WorkOrderForm
from apps.manufacturing.models import (BillOfMaterial, BillOfMaterialLine,
                                        WorkOrder, WorkOrderMaterialRequirement)
from apps.manufacturing import services as mfg

ZERO = Decimal('0.00')


def _company(request):
    return get_company(request.user)


def _next_number(company, prefix):
    return get_sequence_next(f'{prefix}{company.pk}', prefix=prefix, padding=4)


# ──────────────────────────────── Dashboard ──────────────────────────────────

@login_required
def dashboard(request):
    company = _company(request)
    total_boms = BillOfMaterial.objects.filter(company=company, is_active=True).count()
    open_orders = WorkOrder.objects.filter(
        company=company, status__in=[WorkOrder.Status.DRAFT, WorkOrder.Status.IN_PROGRESS]
    ).count()
    done_orders = WorkOrder.objects.filter(company=company, status=WorkOrder.Status.DONE).count()
    recent_orders = WorkOrder.objects.filter(company=company).select_related('product', 'bom')[:8]
    recent_boms = BillOfMaterial.objects.filter(company=company).select_related('product')[:6]
    return render(request, 'apps/manufacturing/dashboard.html', {
        'total_boms': total_boms,
        'open_orders': open_orders,
        'done_orders': done_orders,
        'recent_orders': recent_orders,
        'recent_boms': recent_boms,
    })


# ─────────────────────────── Bills of Material ───────────────────────────────

@login_required
def bom_list(request):
    company = _company(request)
    q = request.GET.get('q', '').strip()
    qs = BillOfMaterial.objects.filter(company=company).select_related('product')
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(number__icontains=q) | Q(product__name__icontains=q))
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/manufacturing/bom_list.html', {'page_obj': page, 'q': q})


@login_required
def bom_detail(request, pk):
    company = _company(request)
    bom = get_object_or_404(
        BillOfMaterial.objects.select_related('product', 'warehouse'), pk=pk, company=company
    )
    lines = bom.lines.select_related('component')
    work_orders = bom.work_orders.select_related('product', 'warehouse')[:10]
    return render(request, 'apps/manufacturing/bom_detail.html', {
        'bom': bom, 'lines': lines, 'work_orders': work_orders,
    })


@login_required
@roles_required('manufacturing', 'admin')
def bom_create(request):
    company = _company(request)
    LineFormSet = inlineformset_factory(
        BillOfMaterial, BillOfMaterialLine, form=BOMLineForm,
        extra=3, can_delete=True, min_num=1, validate_min=True
    )
    if request.method == 'POST':
        form = BOMForm(request.POST, company=company)
        formset = LineFormSet(request.POST, form_kwargs={'company': company})
        if form.is_valid() and formset.is_valid():
            bom = form.save(company=company, user=request.user)
            formset.instance = bom
            formset.save()
            messages.success(request, f'BOM {bom.number} created.')
            return redirect('manufacturing:bom_detail', pk=bom.pk)
    else:
        form = BOMForm(company=company)
        formset = LineFormSet(form_kwargs={'company': company})
    return render(request, 'apps/manufacturing/bom_form.html', {
        'form': form, 'formset': formset, 'title': 'New Bill of Material',
    })


@login_required
@roles_required('manufacturing', 'admin')
def bom_edit(request, pk):
    company = _company(request)
    bom = get_object_or_404(BillOfMaterial, pk=pk, company=company)
    LineFormSet = inlineformset_factory(
        BillOfMaterial, BillOfMaterialLine, form=BOMLineForm,
        extra=1, can_delete=True
    )
    if request.method == 'POST':
        form = BOMForm(request.POST, instance=bom, company=company)
        formset = LineFormSet(request.POST, instance=bom, form_kwargs={'company': company})
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'BOM updated.')
            return redirect('manufacturing:bom_detail', pk=bom.pk)
    else:
        form = BOMForm(instance=bom, company=company)
        formset = LineFormSet(instance=bom, form_kwargs={'company': company})
    return render(request, 'apps/manufacturing/bom_form.html', {
        'form': form, 'formset': formset, 'title': 'Edit BOM', 'bom': bom,
    })


@login_required
@require_POST
@roles_required('manufacturing', 'admin')
def bom_delete(request, pk):
    company = _company(request)
    bom = get_object_or_404(BillOfMaterial, pk=pk, company=company)
    name = bom.name
    bom.delete()
    messages.success(request, f'BOM "{name}" deleted.')
    return redirect('manufacturing:bom_list')


# ─────────────────────────────── Work Orders ─────────────────────────────────

@login_required
def workorder_list(request):
    company = _company(request)
    status = request.GET.get('status', '')
    qs = WorkOrder.objects.filter(company=company).select_related('product', 'bom', 'warehouse')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/manufacturing/workorder_list.html', {
        'page_obj': page,
        'status': status,
        'status_choices': WorkOrder.Status.choices,
    })


@login_required
def workorder_detail(request, pk):
    company = _company(request)
    wo = get_object_or_404(
        WorkOrder.objects.select_related('bom', 'product', 'warehouse', 'created_by'),
        pk=pk, company=company
    )
    materials = wo.materials.select_related('component')
    return render(request, 'apps/manufacturing/workorder_detail.html', {
        'wo': wo, 'materials': materials,
    })


@login_required
@roles_required('manufacturing', 'admin')
def workorder_create(request):
    company = _company(request)
    form = WorkOrderForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        wo = form.save(company=company, user=request.user)
        wo.number = _next_number(company, 'WO')
        wo.save(update_fields=['number'])
        # Auto-create material requirements from BOM lines
        for line in wo.bom.lines.select_related('component'):
            WorkOrderMaterialRequirement.objects.create(
                order=wo,
                component=line.component,
                required=line.quantity * wo.quantity,
                consumed=ZERO,
            )
        messages.success(request, f'Work Order {wo.number} created.')
        return redirect('manufacturing:workorder_detail', pk=wo.pk)
    return render(request, 'apps/manufacturing/workorder_form.html', {
        'form': form, 'title': 'New Work Order',
    })


@login_required
@roles_required('manufacturing', 'admin')
def workorder_start(request, pk):
    company = _company(request)
    wo = get_object_or_404(WorkOrder, pk=pk, company=company)
    if wo.status != WorkOrder.Status.DRAFT:
        messages.error(request, 'Only draft work orders can be started.')
        return redirect('manufacturing:workorder_detail', pk=wo.pk)
    try:
        mfg.start_work_order(wo)
        messages.success(request, f'{wo.number} started.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('manufacturing:workorder_detail', pk=wo.pk)


@login_required
@roles_required('manufacturing', 'admin')
def workorder_finish(request, pk):
    """Mark a work order done: consume components from stock, add finished product to stock."""
    from apps.inventory.services import apply_stock_movement
    from apps.inventory.models import StockMovement

    company = _company(request)
    wo = get_object_or_404(WorkOrder, pk=pk, company=company)
    if wo.status != WorkOrder.Status.IN_PROGRESS:
        messages.error(request, 'Only in-progress work orders can be finished.')
        return redirect('manufacturing:workorder_detail', pk=wo.pk)

    try:
        mfg.complete_work_order(wo)
        messages.success(request, f'{wo.number} finished. Stock updated.')
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('manufacturing:workorder_detail', pk=wo.pk)


@login_required
@roles_required('manufacturing', 'admin')
def workorder_cancel(request, pk):
    company = _company(request)
    wo = get_object_or_404(WorkOrder, pk=pk, company=company)
    if wo.status == WorkOrder.Status.DONE:
        messages.error(request, 'Finished work orders cannot be cancelled.')
        return redirect('manufacturing:workorder_detail', pk=wo.pk)
    wo.status = WorkOrder.Status.CANCELLED
    wo.save(update_fields=['status'])
    messages.success(request, f'{wo.number} cancelled.')
    return redirect('manufacturing:workorder_detail', pk=wo.pk)


# ---------------------------------------------------------------------------
# Edit / Delete for Work Orders
# ---------------------------------------------------------------------------

@login_required
@roles_required('manufacturing', 'admin')
def workorder_edit(request, pk):
    company = _company(request)
    wo = get_object_or_404(WorkOrder, pk=pk, company=company)
    if wo.status not in (WorkOrder.Status.DRAFT,):
        messages.error(request, 'Only draft work orders can be edited.')
        return redirect('manufacturing:workorder_detail', pk=pk)
    from apps.manufacturing.forms import WorkOrderForm
    if request.method == 'POST':
        form = WorkOrderForm(request.POST, instance=wo, company=company)
        if form.is_valid():
            form.save(company=company)
            messages.success(request, f'Work Order {wo.number} updated.')
            return redirect('manufacturing:workorder_detail', pk=pk)
    else:
        form = WorkOrderForm(instance=wo, company=company)
    return render(request, 'apps/manufacturing/workorder_form.html', {
        'form': form, 'title': f'Edit Work Order: {wo.number}',
    })


@login_required
@roles_required('manufacturing', 'admin')
@require_POST
def workorder_delete(request, pk):
    company = _company(request)
    wo = get_object_or_404(WorkOrder, pk=pk, company=company)
    if wo.status not in (WorkOrder.Status.DRAFT, WorkOrder.Status.CANCELLED):
        messages.error(request, 'Only draft or cancelled work orders can be deleted.')
        return redirect('manufacturing:workorder_detail', pk=pk)
    wo.delete()
    messages.success(request, f'Work Order deleted.')
    return redirect('manufacturing:workorder_list')
