from django.urls import path

from apps.inventory import views

app_name = 'inventory'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('products/export/', views.product_export, name='product_export'),
    path('products/import/', views.product_import, name='product_import'),
    path('products/new/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('stock/levels/', views.stock_levels, name='stock_levels'),
    path('stock/movements/', views.stock_movements, name='stock_movements'),
    path('stock/adjustments/new/', views.stock_adjustment_create, name='stock_adjustment_create'),
    path('stock/transfers/new/', views.stock_transfer_create, name='stock_transfer_create'),
    # Daftra Stock Vouchers (إدارة الإذون المخزنية)
    path('vouchers/', views.stock_voucher_list, name='stock_voucher_list'),
    path('vouchers/new/', views.stock_voucher_create, name='stock_voucher_create'),
    path('vouchers/<int:pk>/', views.stock_voucher_detail, name='stock_voucher_detail'),
    # Category management
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    # Warehouse management
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/new/', views.warehouse_create, name='warehouse_create'),
    path('warehouses/<int:pk>/edit/', views.warehouse_edit, name='warehouse_edit'),
    path('warehouses/<int:pk>/delete/', views.warehouse_delete, name='warehouse_delete'),
    # Unit of Measure
    path('uom/', views.uom_list, name='uom_list'),
    path('uom/new/', views.uom_create, name='uom_create'),
    path('uom/<int:pk>/edit/', views.uom_edit, name='uom_edit'),
    path('uom/<int:pk>/delete/', views.uom_delete, name='uom_delete'),
]