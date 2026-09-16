from django.urls import path

from apps.inventory import views

app_name = 'inventory'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('products/export/', views.product_export, name='product_export'),
    path('products/new/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('stock/levels/', views.stock_levels, name='stock_levels'),
    path('stock/movements/', views.stock_movements, name='stock_movements'),
    path('stock/adjustments/new/', views.stock_adjustment_create, name='stock_adjustment_create'),
    path('stock/transfers/new/', views.stock_transfer_create, name='stock_transfer_create'),
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
]