from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.core.models import CompanyScoped, TimeStampMixin, User

MONEY = dict(max_digits=14, decimal_places=2)
User = get_user_model()
ZERO = Decimal('0.00')


class Department(CompanyScoped):
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=30, blank=True)
    manager = models.ForeignKey(
        'Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_departments',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='uniq_department_code'),
        ]

    def __str__(self):
        return self.name


class Employee(CompanyScoped):
    EMPLOYMENT_TYPES = [
        ('full_time', 'Full Time / دوام كامل'),
        ('part_time', 'Part Time / دوام جزئي'),
        ('contract', 'Contract / عقد مؤقت'),
    ]
    employee_code = models.CharField(max_length=30)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees'
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    mobile = models.CharField(max_length=60, blank=True)
    national_id = models.CharField(max_length=60, blank=True, help_text='الرقم القومي / الهوية')
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees'
    )
    job_title = models.CharField(max_length=160, blank=True)
    designation = models.CharField(max_length=160, blank=True, help_text='المسمى الوظيفي')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='full_time')
    hired_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    base_salary = models.DecimalField(**MONEY, default=Decimal('0.00'))
    allowances = models.DecimalField(**MONEY, default=Decimal('0.00'), help_text='البدلات الشهرية')
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=100, blank=True)
    iban = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['employee_code']
        constraints = [
            models.UniqueConstraint(fields=['company', 'employee_code'], name='uniq_employee_code'),
        ]

    def __str__(self):
        return f'{self.employee_code} - {self.full_name}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def on_leave(self):
        today = timezone.localdate()
        return LeaveRequest.objects.filter(
            employee=self,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=today,
            end_date__gte=today,
        ).exists()


class Attendance(CompanyScoped):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        LEAVE = 'leave', 'On Leave'
        HOLIDAY = 'holiday', 'Holiday'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField(default=timezone.localdate)
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [
            models.UniqueConstraint(fields=['company', 'employee', 'date'], name='uniq_attendance'),
        ]

    def __str__(self):
        return f'{self.employee} {self.date} {self.get_status_display()}'

    @property
    def worked_minutes(self):
        if not self.clock_in or not self.clock_out:
            return 0
        in_m = self.clock_in.hour * 60 + self.clock_in.minute
        out_m = self.clock_out.hour * 60 + self.clock_out.minute
        return max(out_m - in_m, 0)


class LeaveRequest(CompanyScoped):
    class LeaveType(models.TextChoices):
        ANNUAL = 'annual', 'Annual Leave'
        SICK = 'sick', 'Sick Leave'
        UNPAID = 'unpaid', 'Unpaid Leave'
        MATERNITY = 'maternity', 'Maternity / Paternity'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=12, choices=LeaveType.choices, default=LeaveType.ANNUAL)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_approved'
    )
    approver = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_processed'
    )
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date', '-id']

    def __str__(self):
        return f'{self.employee} {self.get_leave_type_display()} {self.start_date}->{self.end_date}'

    @property
    def days(self):
        return max((self.end_date - self.start_date).days + 1, 0)


class Payslip(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ISSUED = 'issued', 'Issued'
        PAID = 'paid', 'Paid'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    period = models.CharField(max_length=7)  # YYYY-MM
    gross = models.DecimalField(**MONEY, default=Decimal('0.00'))
    deductions = models.DecimalField(**MONEY, default=Decimal('0.00'))
    net = models.DecimalField(**MONEY, default=Decimal('0.00'))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    issued_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-period', '-id']
        constraints = [
            models.UniqueConstraint(fields=['company', 'employee', 'period'], name='uniq_payslip'),
        ]

    def __str__(self):
        return f'{self.employee} {self.period}'

    @property
    def is_balanced(self):
        return self.net == self.gross - self.deductions