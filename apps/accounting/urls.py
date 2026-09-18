from django.urls import path

from apps.accounting import views

app_name = 'accounting'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('general-ledger/', views.general_ledger, name='general_ledger'),
    path('ar-ledger/', views.ar_ledger, name='ar_ledger'),
    path('journal/', views.journal_list, name='journal_list'),
    path('journal/<int:entry_id>/', views.journal_detail, name='journal_detail'),
    path('journal/new/', views.journal_create, name='journal_create'),
    path('journal/<int:entry_id>/edit/', views.journal_edit, name='journal_edit'),
    path('journal/<int:entry_id>/delete/', views.journal_delete, name='journal_delete'),
    path('journal/<int:entry_id>/post/', views.journal_post, name='journal_post'),
    path('journal/<int:entry_id>/void/', views.journal_void, name='journal_void'),
    path('fiscal-year/<int:fy_id>/close/', views.close_year, name='close_year'),
    # Currency
    path('currencies/', views.currency_list, name='currency_list'),
    path('currencies/new/', views.currency_create, name='currency_create'),
    path('currencies/<int:pk>/edit/', views.currency_edit, name='currency_edit'),
    path('currencies/<int:pk>/delete/', views.currency_delete, name='currency_delete'),
    # Payment Terms
    path('payment-terms/', views.paymentterm_list, name='paymentterm_list'),
    path('payment-terms/new/', views.paymentterm_create, name='paymentterm_create'),
    path('payment-terms/<int:pk>/edit/', views.paymentterm_edit, name='paymentterm_edit'),
    path('payment-terms/<int:pk>/delete/', views.paymentterm_delete, name='paymentterm_delete'),
    # Fiscal Years
    path('fiscal-years/', views.fiscalyear_list, name='fiscalyear_list'),
    path('fiscal-years/new/', views.fiscalyear_create, name='fiscalyear_create'),
    path('fiscal-years/<int:pk>/edit/', views.fiscalyear_edit, name='fiscalyear_edit'),
    path('fiscal-years/<int:pk>/delete/', views.fiscalyear_delete, name='fiscalyear_delete'),
]
