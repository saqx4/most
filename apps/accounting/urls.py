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
]
