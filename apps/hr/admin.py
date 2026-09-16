from django.contrib import admin

from .models import Attendance, Department, Employee, LeaveRequest, Payslip


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'manager', 'is_active', 'company')
    list_filter = ('is_active', 'company')
    search_fields = ('name', 'code')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'full_name', 'department', 'job_title', 'is_active', 'company')
    list_filter = ('is_active', 'department', 'company')
    search_fields = ('employee_code', 'first_name', 'last_name', 'email')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'clock_in', 'clock_out', 'status', 'worked_minutes')
    list_filter = ('status', 'date')
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_date', 'end_date', 'leave_type', 'status', 'approved_by')
    list_filter = ('status', 'leave_type')
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'period', 'gross', 'deductions', 'net', 'status', 'issued_on')
    list_filter = ('status', 'period')
    search_fields = ('employee__first_name', 'employee__last_name')