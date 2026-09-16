from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
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
    user = User.objects.get(pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.username}" updated successfully.')
            return redirect('core:user_list')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'core/user_form.html', {'form': form, 'title': f'Edit User: {user.username}', 'edit_user': user})


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
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    status = 'activated' if target.is_active else 'deactivated'
    messages.success(request, f'User "{target.username}" {status}.')
    return redirect('core:user_list')
