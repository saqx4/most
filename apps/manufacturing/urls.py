from django.urls import path

from apps.manufacturing import views

app_name = 'manufacturing'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Bills of Material
    path('bom/', views.bom_list, name='bom_list'),
    path('bom/new/', views.bom_create, name='bom_create'),
    path('bom/<int:pk>/', views.bom_detail, name='bom_detail'),
    path('bom/<int:pk>/edit/', views.bom_edit, name='bom_edit'),
    path('bom/<int:pk>/delete/', views.bom_delete, name='bom_delete'),

    # Work Orders
    path('orders/', views.workorder_list, name='workorder_list'),
    path('orders/new/', views.workorder_create, name='workorder_create'),
    path('orders/<int:pk>/', views.workorder_detail, name='workorder_detail'),
    path('orders/<int:pk>/edit/', views.workorder_edit, name='workorder_edit'),
    path('orders/<int:pk>/delete/', views.workorder_delete, name='workorder_delete'),
    path('orders/<int:pk>/start/', views.workorder_start, name='workorder_start'),
    path('orders/<int:pk>/finish/', views.workorder_finish, name='workorder_finish'),
    path('orders/<int:pk>/cancel/', views.workorder_cancel, name='workorder_cancel'),
]
