from django.urls import path

from apps.purchasing import views

app_name = 'purchasing'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/new/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # Purchase Orders
    path('orders/', views.po_list, name='po_list'),
    path('orders/new/', views.po_create, name='po_create'),
    path('orders/<int:pk>/', views.po_detail, name='po_detail'),
    path('orders/<int:pk>/confirm/', views.po_confirm, name='po_confirm'),
    path('orders/<int:pk>/cancel/', views.po_cancel, name='po_cancel'),
    path('orders/<int:pk>/pdf/', views.po_pdf, name='po_pdf'),

    # Goods Receipts
    path('orders/<int:po_pk>/receive/', views.receipt_create, name='receipt_create'),

    # Supplier Bills
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/new/', views.bill_create, name='bill_create'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('bills/<int:pk>/edit/', views.bill_edit, name='bill_edit'),
    path('bills/<int:pk>/delete/', views.bill_delete, name='bill_delete'),
    path('bills/<int:pk>/post/', views.bill_post, name='bill_post'),

    # Supplier Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/new/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
]
