from django.urls import path

from apps.reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('income-statement/', views.income_statement, name='income_statement'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('account-balances/', views.account_balances_view, name='account_balances'),
]

