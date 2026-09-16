"""Small generic view/equal-plus scaffold shared by all ERP modules.

Every app gets List / Create / Update / Detail / Delete views with:
  * login + role guarding
  * company-scoping on every queryset
  * pagination, keyword search, column ordering
  * ...all through a single base class below so views.py stays tiny.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.decorators import roles_required, module_required
from apps.core.services import get_company


def _scope(request):
    return get_company(request.user)


class ScopeMixin:
    """Applies company scoping + optional warehouse/product filters."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        self.company = _scope(request)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(company=self.company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['company'] = self.company
        return ctx

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        return kw


class ERPListView(ScopeMixin, ListView):
    paginate_by = 25
    search_fields = []
    sort_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q and self.search_fields:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f + '__icontains': q})
            qs = qs.filter(cond)
        sort = self.request.GET.get('sort', '')
        if sort in self.sort_fields:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['list_title'] = getattr(self, 'list_title', self.model._meta.verbose_name_plural.title())
        return ctx


class ERPCreateView(ScopeMixin, CreateView):
    def get_initial(self):
        initial = super().get_initial()
        initial['company'] = self.company
        return initial


class ERPUpdateView(ScopeMixin, UpdateView):
    pass


class ERPDetailView(ScopeMixin, DetailView):
    pass


class ERPDeleteView(ScopeMixin, DeleteView):
    pass