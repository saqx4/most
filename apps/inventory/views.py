from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import roles_required
from apps.core.services import get_company
from apps.inventory.forms import (CategoryForm, ProductForm, StockAdjustmentForm,
                                  StockAdjustmentLineForm, StockTransferForm,
                                  StockTransferLineForm, UnitOfMeasureForm, WarehouseForm)
from apps.inventory.models import (Category, Product, StockLevel, StockMovement,
                                   StockAdjustment, StockAdjustmentLine,
                                   StockTransfer, StockTransferLine, Warehouse)
from apps.inventory import services as inv


def _company(request):
    return get_company(request.user)


@login_required
def product_list(request):
    company = _company(request)
    qs = Product.objects.filter(company=company)
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(sku__icontains=q) | Q(name__icontains=q) | Q(barcode__icontains=q))
    products = list(qs.select_related('category', 'uom'))
    paginator = Paginator(products, 25)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/inventory/product_list.html', {
        'page_obj': page, 'q': q,
    })


@login_required
def product_detail(request, pk):
    company = _company(request)
    product = get_object_or_404(Product, pk=pk, company=company)
    stocks = product.stocks.filter(company=company).select_related('warehouse')
    movements = product.movements.filter(company=company).select_related('warehouse')[:50]
    return render(request, 'apps/inventory/product_detail.html', {
        'product': product, 'stocks': stocks, 'movements': movements,
    })


@login_required
@roles_required('warehouse', 'admin')
def product_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('inventory:product_list')
    form = ProductForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        form.save(company=company, user=request.user)
        messages.success(request, 'Product created.')
        return redirect('inventory:product_list')
    return render(request, 'apps/inventory/product_form.html', {'form': form, 'title': 'New Product'})


@login_required
@roles_required('warehouse', 'admin')
def product_edit(request, pk):
    company = _company(request)
    product = get_object_or_404(Product, pk=pk, company=company)
    form = ProductForm(request.POST or None, instance=product, company=company)
    if request.method == 'POST' and form.is_valid():
        form.save(company=company)
        messages.success(request, 'Product updated.')
        return redirect('inventory:product_detail', pk=product.pk)
    return render(request, 'apps/inventory/product_form.html', {'form': form, 'title': f'Edit {product.sku}'})


@login_required
@require_POST
@roles_required('warehouse', 'admin')
def product_delete(request, pk):
    company = _company(request)
    product = get_object_or_404(Product, pk=pk, company=company)
    sku = product.sku
    product.delete()
    messages.success(request, f'Product "{sku}" deleted.')
    return redirect('inventory:product_list')


@login_required
def stock_levels(request):
    company = _company(request)
    scoped = StockLevel.objects.filter(company=company).select_related('product', 'warehouse')
    warehouse_id = request.GET.get('warehouse', '')
    if warehouse_id:
        scoped = scoped.filter(warehouse_id=warehouse_id)
    rows = list(scoped)
    total_value = sum((r.quantity * r.avg_cost for r in rows), Decimal('0.00'))
    warehouses = company.warehouses.all() if company else []
    return render(request, 'apps/inventory/stock_levels.html', {
        'rows': rows, 'total_value': total_value, 'warehouses': warehouses,
        'warehouse_id': warehouse_id,
    })


@login_required
def stock_movements(request):
    company = _company(request)
    qs = StockMovement.objects.filter(company=company).select_related('product', 'warehouse')
    mtype = request.GET.get('type', '')
    if mtype:
        qs = qs.filter(type=mtype)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'apps/inventory/stock_movements.html', {
        'page_obj': page, 'mtype': mtype,
        'types': StockMovement.MovementType.choices,
    })


def _inline_formset(model, line_model, line_form, request, instance, company):
    from django.forms import inlineformset_factory
    factory = inlineformset_factory(model, line_model, form=line_form, extra=1, can_delete=True)
    return factory(request.POST or None, instance=instance, form_kwargs={'company': company})


@login_required
@roles_required('warehouse', 'admin')
def stock_adjustment_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('inventory:stock_levels')
    form = StockAdjustmentForm(request.POST or None, company=company)
    formset = _inline_formset(StockAdjustment, StockAdjustmentLine, StockAdjustmentLineForm, request, None, company)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        has_lines = any(l.cleaned_data and not l.cleaned_data.get('DELETE') for l in formset.forms)
        if not has_lines:
            messages.error(request, 'Add at least one line.')
        else:
            adjustment = form.save(commit=False)
            adjustment.company = company
            adjustment.number = inv.next_number(company, 'ADJ')
            adjustment.created_by = request.user
            adjustment.save()
            formset.instance = adjustment
            formset.save()
            try:
                inv.post_adjustment(adjustment, user=request.user)
                messages.success(request, f'Adjustment {adjustment.number} posted.')
                return redirect('inventory:stock_levels')
            except ValueError as exc:
                messages.error(request, str(exc))
    return render(request, 'apps/inventory/stock_adjustment_form.html', {'form': form, 'formset': formset})


@login_required
@roles_required('warehouse', 'admin')
def stock_transfer_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('inventory:stock_levels')
    form = StockTransferForm(request.POST or None, company=company)
    formset = _inline_formset(StockTransfer, StockTransferLine, StockTransferLineForm, request, None, company)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        has_lines = any(l.cleaned_data and not l.cleaned_data.get('DELETE') for l in formset.forms)
        if not has_lines:
            messages.error(request, 'Add at least one line item.')
        else:
            transfer = form.save(commit=False)
            transfer.company = company
            transfer.number = inv.next_number(company, 'ST')
            transfer.created_by = request.user
            transfer.save()
            formset.instance = transfer
            formset.save()
            try:
                inv.post_transfer(transfer, user=request.user)
                messages.success(request, f'Transfer {transfer.number} posted.')
                return redirect('inventory:stock_movements')
            except ValueError as exc:
                messages.error(request, str(exc))
    return render(request, 'apps/inventory/stock_transfer_form.html', {'form': form, 'formset': formset})


@login_required
def product_export(request):
    company = _company(request)
    fmt = request.GET.get('format', 'csv')
    fields = ['sku', 'name', 'purchase_price', 'sale_price', 'is_service', 'is_active']
    qs = Product.objects.filter(company=company).order_by('sku')
    from apps.core.export import export_to_csv, export_to_excel
    if fmt == 'xlsx':
        return export_to_excel(qs, fields, 'products.xlsx')
    return export_to_csv(qs, fields, 'products.csv')


@login_required
@roles_required('warehouse', 'admin')
def product_import(request):
    company = _company(request)
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Please upload a file.')
            return redirect('inventory:product_list')
        from apps.core.export import import_products_from_file
        count, errors = import_products_from_file(file, company, user=request.user)
        if errors:
            for e in errors[:5]:
                messages.warning(request, e)
        messages.success(request, f'{count} product(s) imported successfully.')
        return redirect('inventory:product_list')
    return render(request, 'apps/inventory/product_import.html')


# ---------------------------------------------------------------------------
# Category Management
# ---------------------------------------------------------------------------

@login_required
@roles_required('warehouse', 'admin')
def category_list(request):
    company = _company(request)
    q = request.GET.get('q', '').strip()
    cats = Category.objects.filter(company=company).select_related('parent').order_by('name')
    if q:
        cats = cats.filter(name__icontains=q)
    return render(request, 'apps/inventory/category_list.html', {'categories': cats, 'q': q})


@login_required
@roles_required('warehouse', 'admin')
def category_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('inventory:category_list')
    if request.method == 'POST':
        form = CategoryForm(request.POST, company=company)
        if form.is_valid():
            form.save(company=company)
            messages.success(request, 'Category created.')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(company=company)
    return render(request, 'apps/inventory/category_form.html', {'form': form, 'title': 'Create Category'})


@login_required
@roles_required('warehouse', 'admin')
def category_edit(request, pk):
    company = _company(request)
    cat = get_object_or_404(Category, pk=pk, company=company)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=cat, company=company)
        if form.is_valid():
            form.save(company=company)
            messages.success(request, 'Category updated.')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=cat, company=company)
    return render(request, 'apps/inventory/category_form.html', {'form': form, 'title': f'Edit Category: {cat.name}'})


@login_required
@roles_required('warehouse', 'admin')
@require_POST
def category_delete(request, pk):
    company = _company(request)
    cat = get_object_or_404(Category, pk=pk, company=company)
    cat.delete()
    messages.success(request, f'Category "{cat.name}" deleted.')
    return redirect('inventory:category_list')


# ---------------------------------------------------------------------------
# Warehouse Management
# ---------------------------------------------------------------------------

@login_required
@roles_required('warehouse', 'admin')
def warehouse_list(request):
    company = _company(request)
    warehouses = Warehouse.objects.filter(company=company).order_by('name')
    return render(request, 'apps/inventory/warehouse_list.html', {'warehouses': warehouses})


@login_required
@roles_required('warehouse', 'admin')
def warehouse_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('inventory:warehouse_list')
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            wh = form.save(commit=False)
            wh.company = company
            wh.save()
            messages.success(request, f'Warehouse "{wh.name}" created.')
            return redirect('inventory:warehouse_list')
    else:
        form = WarehouseForm()
    return render(request, 'apps/inventory/warehouse_form.html', {'form': form, 'title': 'Create Warehouse'})


@login_required
@roles_required('warehouse', 'admin')
def warehouse_edit(request, pk):
    company = _company(request)
    wh = get_object_or_404(Warehouse, pk=pk, company=company)
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=wh)
        if form.is_valid():
            form.save()
            messages.success(request, f'Warehouse "{wh.name}" updated.')
            return redirect('inventory:warehouse_list')
    else:
        form = WarehouseForm(instance=wh)
    return render(request, 'apps/inventory/warehouse_form.html', {'form': form, 'title': f'Edit Warehouse: {wh.name}'})


@login_required
@roles_required('warehouse', 'admin')
@require_POST
def warehouse_delete(request, pk):
    company = _company(request)
    wh = get_object_or_404(Warehouse, pk=pk, company=company)
    wh.delete()
    messages.success(request, f'Warehouse "{wh.name}" deleted.')
    return redirect('inventory:warehouse_list')


# ---------------------------------------------------------------------------
# Daftra Stock Vouchers (أذون المخزن)
# ---------------------------------------------------------------------------
@login_required
@roles_required('warehouse', 'admin')
def stock_voucher_list(request):
    company = _company(request)
    from apps.inventory.models import StockVoucher
    vouchers = StockVoucher.objects.filter(company=company).select_related('warehouse', 'to_warehouse')
    v_type = request.GET.get('type')
    if v_type:
        vouchers = vouchers.filter(voucher_type=v_type)
    return render(request, 'apps/inventory/voucher_list.html', {'vouchers': vouchers, 'v_type': v_type})


@login_required
@roles_required('warehouse', 'admin')
def stock_voucher_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('inventory:stock_voucher_list')

    from apps.inventory.models import StockVoucher, StockVoucherLine
    from apps.inventory.forms import StockVoucherForm, StockVoucherLineForm
    from django.forms import inlineformset_factory

    LineFormSet = inlineformset_factory(StockVoucher, StockVoucherLine, form=StockVoucherLineForm, extra=2, can_delete=True, min_num=1, validate_min=True)

    if request.method == 'POST':
        form = StockVoucherForm(request.POST, company=company)
        formset = LineFormSet(request.POST, form_kwargs={'company': company})
        if form.is_valid() and formset.is_valid():
            voucher = form.save(commit=False)
            voucher.company = company
            voucher.created_by = request.user
            from apps.sales.services import next_number
            voucher.number = next_number(company, 'VCH')
            voucher.save()
            formset.instance = voucher
            formset.save()
            messages.success(request, f'Stock voucher {voucher.number} created.')
            return redirect('inventory:stock_voucher_detail', pk=voucher.pk)
    else:
        form = StockVoucherForm(company=company)
        formset = LineFormSet(form_kwargs={'company': company})

    return render(request, 'apps/inventory/voucher_form.html', {'form': form, 'formset': formset})


@login_required
@roles_required('warehouse', 'admin')
def stock_voucher_detail(request, pk):
    company = _company(request)
    from apps.inventory.models import StockVoucher
    voucher = get_object_or_404(StockVoucher.objects.select_related('warehouse', 'to_warehouse', 'created_by'), pk=pk, company=company)
    lines = voucher.lines.select_related('product')
    return render(request, 'apps/inventory/voucher_detail.html', {'voucher': voucher, 'lines': lines})


# ---------------------------------------------------------------------------
# Unit of Measure Management
# ---------------------------------------------------------------------------
@login_required
@roles_required('warehouse', 'admin')
def uom_list(request):
    from apps.inventory.models import UnitOfMeasure
    uoms = UnitOfMeasure.objects.all().order_by('code')
    return render(request, 'apps/inventory/uom_list.html', {'uoms': uoms})


@login_required
@roles_required('warehouse', 'admin')
def uom_create(request):
    from apps.inventory.models import UnitOfMeasure
    if request.method == 'POST':
        form = UnitOfMeasureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit of measure created.')
            return redirect('inventory:uom_list')
    else:
        form = UnitOfMeasureForm()
    return render(request, 'apps/inventory/uom_form.html', {'form': form, 'title': 'New Unit of Measure'})


@login_required
@roles_required('warehouse', 'admin')
def uom_edit(request, pk):
    from apps.inventory.models import UnitOfMeasure
    uom = get_object_or_404(UnitOfMeasure, pk=pk)
    if request.method == 'POST':
        form = UnitOfMeasureForm(request.POST, instance=uom)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit of measure updated.')
            return redirect('inventory:uom_list')
    else:
        form = UnitOfMeasureForm(instance=uom)
    return render(request, 'apps/inventory/uom_form.html', {'form': form, 'title': f'Edit {uom.code}'})


@login_required
@require_POST
@roles_required('warehouse', 'admin')
def uom_delete(request, pk):
    from apps.inventory.models import UnitOfMeasure
    uom = get_object_or_404(UnitOfMeasure, pk=pk)
    uom.delete()
    messages.success(request, f'Unit of measure "{uom.code}" deleted.')
    return redirect('inventory:uom_list')