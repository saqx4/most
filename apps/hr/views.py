from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import roles_required
from apps.core.services import get_company
from apps.hr.forms import DepartmentForm, EmployeeForm, PayslipForm
from apps.hr.models import Attendance, Department, Employee, LeaveRequest, Payslip

ZERO = Decimal('0.00')


def _company(request):
    return get_company(request.user)


def _period_now(now=None):
    now = now or timezone.localdate()
    return f'{now.year}-{now.month:02d}'


@login_required
def dashboard(request):
    company = _company(request)
    today = timezone.localdate()
    period = _period_now(today)

    headcount = Employee.objects.filter(company=company, is_active=True).count()
    on_leave = LeaveRequest.objects.filter(
        company=company,
        status=LeaveRequest.Status.APPROVED,
        start_date__lte=today,
        end_date__gte=today,
    ).values('employee').distinct().count()
    month_net = Payslip.objects.filter(company=company, period=period).aggregate(
        t=Sum('net')
    )['t'] or ZERO

    employees = Employee.objects.filter(company=company).select_related('department')[:6]
    pending_leaves = LeaveRequest.objects.filter(
        company=company, status=LeaveRequest.Status.PENDING
    ).select_related('employee')[:6]
    recent_payslips = Payslip.objects.filter(company=company).select_related('employee')[:6]

    return render(request, 'apps/hr/dashboard.html', {
        'company': company,
        'headcount': headcount,
        'on_leave': on_leave,
        'month_net': month_net,
        'period': period,
        'employees': employees,
        'pending_leaves': pending_leaves,
        'recent_payslips': recent_payslips,
    })


@login_required
@roles_required('hr', 'admin')
def employee_list(request):
    company = _company(request)
    q = request.GET.get('q', '').strip()
    employees = Employee.objects.filter(company=company).select_related('department', 'user')
    if q:
        employees = employees.filter(
            first_name__icontains=q
        ) | employees.filter(last_name__icontains=q) | employees.filter(employee_code__icontains=q)
    return render(request, 'apps/hr/employee_list.html', {
        'employees': employees, 'q': q,
    })


@login_required
@roles_required('hr', 'admin')
def employee_detail(request, employee_id):
    company = _company(request)
    employee = get_object_or_404(
        Employee.objects.select_related('department', 'user'), pk=employee_id, company=company
    )
    attendance = Attendance.objects.filter(company=company, employee=employee)[:10]
    leaves = LeaveRequest.objects.filter(company=company, employee=employee)[:10]
    payslips = Payslip.objects.filter(company=company, employee=employee)[:10]
    return render(request, 'apps/hr/employee_detail.html', {
        'employee': employee, 'attendance': attendance, 'leaves': leaves, 'payslips': payslips,
    })


@login_required
@roles_required('hr', 'admin')
def employee_create(request):
    company = _company(request)
    form = EmployeeForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        employee = form.save()
        messages.success(request, f'Employee {employee.employee_code} created.')
        return redirect('hr:employee_detail', employee_id=employee.pk)
    return render(request, 'apps/hr/employee_form.html', {'form': form})


@login_required
@roles_required('hr', 'admin')
def employee_edit(request, employee_id):
    company = _company(request)
    employee = get_object_or_404(Employee, pk=employee_id, company=company)
    form = EmployeeForm(request.POST or None, instance=employee, company=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Employee {employee.employee_code} updated.')
        return redirect('hr:employee_detail', employee_id=employee.pk)
    return render(request, 'apps/hr/employee_form.html', {'form': form, 'title': f'Edit {employee.full_name}'})


@login_required
@require_POST
@roles_required('hr', 'admin')
def employee_delete(request, employee_id):
    company = _company(request)
    employee = get_object_or_404(Employee, pk=employee_id, company=company)
    code = employee.employee_code
    employee.delete()
    messages.success(request, f'Employee "{code}" deleted.')
    return redirect('hr:employee_list')


@login_required
@roles_required('hr', 'admin')
def department_list(request):
    company = _company(request)
    departments = Department.objects.filter(company=company).prefetch_related('employees')
    return render(request, 'apps/hr/department_list.html', {'departments': departments})


@login_required
@roles_required('hr', 'admin')
def attendance_list(request):
    company = _company(request)
    date = request.GET.get('date', '')
    entries = Attendance.objects.filter(company=company).select_related('employee').order_by(
        '-date', '-id'
    )
    if date:
        entries = entries.filter(date=date)
    return render(request, 'apps/hr/attendance_list.html', {
        'entries': entries[:100], 'date': date,
    })


@login_required
@roles_required('hr', 'admin')
def leave_list(request):
    company = _company(request)
    status = request.GET.get('status', '')
    leaves = LeaveRequest.objects.filter(company=company).select_related('employee', 'approved_by')
    if status:
        leaves = leaves.filter(status=status)
    return render(request, 'apps/hr/leave_list.html', {
        'leaves': leaves, 'status': status,
    })


@login_required
@roles_required('hr', 'admin')
def payslip_list(request):
    company = _company(request)
    period = request.GET.get('period', '')
    payslips = Payslip.objects.filter(company=company).select_related('employee')
    if period:
        payslips = payslips.filter(period=period)
    total_gross = payslips.aggregate(t=Sum('gross'))['t'] or ZERO
    total_net = payslips.aggregate(t=Sum('net'))['t'] or ZERO
    return render(request, 'apps/hr/payslip_list.html', {
        'payslips': payslips, 'period': period,
        'total_gross': total_gross, 'total_net': total_net,
    })


@login_required
@roles_required('hr', 'admin')
def payslip_pdf(request, pk):
    company = _company(request)
    payslip = get_object_or_404(Payslip.objects.select_related('employee', 'employee__department'), pk=pk, company=company)
    from apps.core.pdf import render_to_pdf
    return render_to_pdf('pdf/payslip.html', {
        'payslip': payslip, 'company': company,
    }, filename=f'payslip-{payslip.employee.employee_code}-{payslip.period}.pdf')


@login_required
@roles_required('hr', 'admin')
def payslip_create(request):
    company = _company(request)
    form = PayslipForm(request.POST or None, company=company, initial={'period': _period_now()})
    if request.method == 'POST' and form.is_valid():
        payslip = form.save()
        messages.success(request, f'Payslip for {payslip.employee} ({payslip.period}) created.')
        return redirect('hr:payslip_list')
    return render(request, 'apps/hr/payslip_form.html', {'form': form})


@login_required
@require_POST
@roles_required('hr', 'admin')
def payslip_send_email(request, pk):
    company = _company(request)
    payslip = get_object_or_404(Payslip.objects.select_related('employee'), pk=pk, company=company)
    if not payslip.employee.email:
        messages.error(request, f'Employee {payslip.employee.full_name} has no email address.')
        return redirect('hr:payslip_list')
    from apps.core.email import send_payslip_email
    send_payslip_email(payslip)
    messages.success(request, f'Payslip emailed to {payslip.employee.full_name}.')
    return redirect('hr:payslip_list')


@login_required
@roles_required('hr', 'admin')
def employee_export(request):
    company = _company(request)
    fmt = request.GET.get('format', 'csv')
    fields = ['employee_code', 'first_name', 'last_name', 'email', 'phone', 'job_title', 'is_active']
    qs = Employee.objects.filter(company=company).order_by('employee_code')
    from apps.core.export import export_to_csv, export_to_excel
    if fmt == 'xlsx':
        return export_to_excel(qs, fields, 'employees.xlsx')
    return export_to_csv(qs, fields, 'employees.csv')


# ---------------------------------------------------------------------------
# Department CRUD
# ---------------------------------------------------------------------------

@login_required
@roles_required('hr', 'admin')
def department_create(request):
    company = _company(request)
    if company is None:
        messages.error(request, 'No company configured yet.')
        return redirect('hr:department_list')
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.company = company
            dept.save()
            messages.success(request, f'Department "{dept.name}" created.')
            return redirect('hr:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'apps/hr/department_form.html', {'form': form, 'title': 'Create Department'})


@login_required
@roles_required('hr', 'admin')
def department_edit(request, pk):
    company = _company(request)
    dept = get_object_or_404(Department, pk=pk, company=company)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, f'Department "{dept.name}" updated.')
            return redirect('hr:department_list')
    else:
        form = DepartmentForm(instance=dept)
    return render(request, 'apps/hr/department_form.html', {'form': form, 'title': f'Edit Department: {dept.name}'})


@login_required
@roles_required('hr', 'admin')
@require_POST
def department_delete(request, pk):
    company = _company(request)
    dept = get_object_or_404(Department, pk=pk, company=company)
    dept.delete()
    messages.success(request, f'Department "{dept.name}" deleted.')
    return redirect('hr:department_list')


# ---------------------------------------------------------------------------
# Payslip Edit / Delete
# ---------------------------------------------------------------------------

@login_required
@roles_required('hr', 'admin')
def payslip_edit(request, pk):
    company = _company(request)
    payslip = get_object_or_404(Payslip, pk=pk, company=company)
    if request.method == 'POST':
        form = PayslipForm(request.POST, instance=payslip, company=company)
        if form.is_valid():
            form.save()
            messages.success(request, f'Payslip updated.')
            return redirect('hr:payslip_list')
    else:
        form = PayslipForm(instance=payslip, company=company)
    return render(request, 'apps/hr/payslip_form.html', {'form': form, 'title': f'Edit Payslip: {payslip.employee}'})


@login_required
@roles_required('hr', 'admin')
@require_POST
def payslip_delete(request, pk):
    company = _company(request)
    payslip = get_object_or_404(Payslip, pk=pk, company=company)
    payslip.delete()
    messages.success(request, f'Payslip deleted.')
    return redirect('hr:payslip_list')