from django.urls import path

from apps.sales import views

app_name = 'sales'

urlpatterns = [
    # Billing management
    path('billing/', views.billing_management, name='billing_management'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # Sales orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/new/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/', views.order_edit, name='order_edit'),
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),
    path('orders/<int:pk>/confirm/', views.order_confirm, name='order_confirm'),

    # Quotes
    path('quotes/', views.quote_list, name='quote_list'),
    path('quotes/new/', views.quote_create, name='quote_create'),
    path('quotes/<int:pk>/', views.quote_detail, name='quote_detail'),
    path('quotes/<int:pk>/edit/', views.quote_edit, name='quote_edit'),
    path('quotes/<int:pk>/delete/', views.quote_delete, name='quote_delete'),
    path('quotes/<int:pk>/send/', views.quote_send, name='quote_send'),
    path('quotes/<int:pk>/accept/', views.quote_accept, name='quote_accept'),
    path('quotes/<int:pk>/reject/', views.quote_reject, name='quote_reject'),
    path('quotes/<int:pk>/pdf/', views.quote_pdf, name='quote_pdf'),
    path('quotes/<int:pk>/convert/', views.quote_convert_to_order, name='quote_convert_to_order'),

    # Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/new/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:pk>/mark-paid/', views.invoice_mark_paid, name='invoice_mark_paid'),
    path('invoices/<int:pk>/send/', views.invoice_send_email, name='invoice_send_email'),
    path('customers/export/', views.customer_export, name='customer_export'),

    # Credit notes (Returned Invoices)
    path('credit-notes/', views.creditnote_list, name='creditnote_list'),
    path('credit-notes/new/', views.creditnote_create, name='creditnote_create'),
    path('credit-notes/<int:pk>/', views.creditnote_detail, name='creditnote_detail'),
    path('credit-notes/<int:pk>/post/', views.creditnote_post, name='creditnote_post'),
    path('credit-notes/<int:pk>/delete/', views.creditnote_delete, name='creditnote_delete'),

    # Periodic Invoices
    path('periodic/', views.periodic_list, name='periodic_list'),
    path('periodic/new/', views.periodic_create, name='periodic_create'),
    path('periodic/<int:pk>/', views.periodic_detail, name='periodic_detail'),
    path('periodic/<int:pk>/toggle/', views.periodic_toggle, name='periodic_toggle'),

    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/new/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),

    # Sales Settings
    path('settings/', views.sales_settings, name='sales_settings'),
]