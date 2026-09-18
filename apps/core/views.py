from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.core.decorators import roles_required
from apps.core.forms import UserCreateForm, UserEditForm
from apps.core.models import User


class LogInView(auth_views.LoginView):
    template_name = 'registration/login.html'


@require_GET
@login_required
def dashboard(request):
    return redirect('reports:dashboard')


@login_required
def profile(request):
    return render(request, 'core/profile.html')


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@login_required
@roles_required('admin', 'manager')
def user_list(request):
    q = request.GET.get('q', '').strip()
    users = User.objects.select_related('role').order_by('-is_active', 'username')
    if q:
        users = users.filter(username__icontains=q) | users.filter(first_name__icontains=q) | users.filter(last_name__icontains=q) | users.filter(email__icontains=q)
    return render(request, 'core/user_list.html', {'users': users, 'q': q})


@login_required
@roles_required('admin', 'manager')
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('core:user_list')
    else:
        form = UserCreateForm()
    return render(request, 'core/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
@roles_required('admin', 'manager')
def user_edit(request, pk):
    target = User.objects.get(pk=pk)
    if target.is_superuser:
        messages.error(request, 'Cannot edit superuser accounts.')
        return redirect('core:user_list')
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{target.username}" updated successfully.')
            return redirect('core:user_list')
    else:
        form = UserEditForm(instance=target)
    return render(request, 'core/user_form.html', {'form': form, 'title': f'Edit User: {target.username}', 'edit_user': target})


@login_required
@roles_required('admin', 'manager')
@require_POST
def user_delete(request, pk):
    target = User.objects.get(pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('core:user_list')
    if target.is_superuser:
        messages.error(request, 'Cannot delete superuser accounts.')
        return redirect('core:user_list')
    username = target.username
    target.delete()
    messages.success(request, f'User "{username}" deleted.')
    return redirect('core:user_list')


@login_required
@roles_required('admin', 'manager')
@require_POST
def user_toggle_active(request, pk):
    target = User.objects.get(pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('core:user_list')
    if target.is_superuser:
        messages.error(request, 'Cannot deactivate superuser accounts.')
        return redirect('core:user_list')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    status = 'activated' if target.is_active else 'deactivated'
    messages.success(request, f'User "{target.username}" {status}.')
    return redirect('core:user_list')


@login_required
@roles_required('admin', 'manager')
def activity_log(request):
    from apps.core.models import AuditLog
    logs = AuditLog.objects.all().select_related('user').order_by('-created_at')
    model_filter = request.GET.get('model', '')
    if model_filter:
        logs = logs.filter(model=model_filter)
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    paginator = Paginator(logs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/activity_log.html', {'page_obj': page, 'model_filter': model_filter, 'action_filter': action_filter})


@login_required
def global_search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    from django.db.models import Q
    results = []
    company = getattr(request.user, 'company', None)

    # Customers
    from apps.sales.models import Customer
    for c in Customer.objects.filter(
        Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(tax_id__icontains=q),
        company=company, is_active=True
    )[:5]:
        results.append({
            'type': 'Customer', 'icon': 'ri-user-3-line', 'color': 'text-blue-500',
            'title': c.name, 'subtitle': c.email or c.phone or '',
            'url': f'/sales/customers/{c.pk}/',
        })

    # Products
    from apps.inventory.models import Product
    for p in Product.objects.filter(
        Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q),
        company=company, is_active=True
    )[:5]:
        results.append({
            'type': 'Product', 'icon': 'ri-archive-line', 'color': 'text-emerald-500',
            'title': p.name, 'subtitle': p.sku,
            'url': f'/inventory/products/{p.pk}/',
        })

    # Invoices
    from apps.sales.models import SalesInvoice
    for inv in SalesInvoice.objects.filter(
        Q(number__icontains=q) | Q(customer__name__icontains=q),
        company=company
    )[:5]:
        results.append({
            'type': 'Invoice', 'icon': 'ri-file-text-line', 'color': 'text-indigo-500',
            'title': inv.number, 'subtitle': f'{inv.customer.name} — {inv.status}',
            'url': f'/sales/invoices/{inv.pk}/',
        })

    # Orders
    from apps.sales.models import SalesOrder
    for o in SalesOrder.objects.filter(
        Q(number__icontains=q) | Q(customer__name__icontains=q),
        company=company
    )[:5]:
        results.append({
            'type': 'Order', 'icon': 'ri-shopping-bag-3-line', 'color': 'text-amber-500',
            'title': o.number, 'subtitle': f'{o.customer.name} — {o.status}',
            'url': f'/sales/orders/{o.pk}/',
        })

    # Quotes
    from apps.sales.models import SalesQuote
    for qt in SalesQuote.objects.filter(
        Q(number__icontains=q) | Q(customer__name__icontains=q),
        company=company
    )[:5]:
        results.append({
            'type': 'Quote', 'icon': 'ri-file-copy-line', 'color': 'text-cyan-500',
            'title': qt.number, 'subtitle': f'{qt.customer.name} — {qt.status}',
            'url': f'/sales/quotes/{qt.pk}/',
        })

    # Suppliers
    from apps.purchasing.models import Supplier
    for s in Supplier.objects.filter(
        Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q),
        company=company, is_active=True
    )[:5]:
        results.append({
            'type': 'Supplier', 'icon': 'ri-truck-line', 'color': 'text-orange-500',
            'title': s.name, 'subtitle': s.email or s.phone or '',
            'url': f'/purchasing/suppliers/{s.pk}/',
        })

    # Purchase Orders
    from apps.purchasing.models import PurchaseOrder
    for po in PurchaseOrder.objects.filter(
        Q(number__icontains=q) | Q(supplier__name__icontains=q),
        company=company
    )[:5]:
        results.append({
            'type': 'Purchase Order', 'icon': 'ri-file-list-3-line', 'color': 'text-teal-500',
            'title': po.number, 'subtitle': f'{po.supplier.name} — {po.status}',
            'url': f'/purchasing/orders/{po.pk}/',
        })

    # Employees
    from apps.hr.models import Employee
    for e in Employee.objects.filter(
        Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(employee_code__icontains=q),
        company=company, is_active=True
    )[:5]:
        results.append({
            'type': 'Employee', 'icon': 'ri-team-line', 'color': 'text-pink-500',
            'title': e.full_name, 'subtitle': e.job_title or e.employee_code,
            'url': f'/hr/employees/{e.pk}/',
        })

    return JsonResponse({'results': results})
