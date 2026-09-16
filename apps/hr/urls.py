from django.urls import path

from apps.hr import views

app_name = 'hr'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/new/', views.employee_create, name='employee_create'),
    path('employees/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:employee_id>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),
    path('employees/export/', views.employee_export, name='employee_export'),
    path('departments/', views.department_list, name='department_list'),
    path('departments/new/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('leaves/', views.leave_list, name='leave_list'),
    path('payslips/', views.payslip_list, name='payslip_list'),
    path('payslips/<int:pk>/pdf/', views.payslip_pdf, name='payslip_pdf'),
    path('payslips/new/', views.payslip_create, name='payslip_create'),
    path('payslips/<int:pk>/edit/', views.payslip_edit, name='payslip_edit'),
    path('payslips/<int:pk>/delete/', views.payslip_delete, name='payslip_delete'),
    path('payslips/<int:pk>/send/', views.payslip_send_email, name='payslip_send_email'),
]