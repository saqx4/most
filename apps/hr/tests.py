from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company
from apps.hr.models import Attendance, Department, Employee, LeaveRequest, Payslip


class HRModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Test Co')
        self.dept = Department.objects.create(company=self.company, name='Engineering', code='ENG')
        self.employee = Employee.objects.create(
            company=self.company, employee_code='E1',
            first_name='Jo', last_name='Doe', department=self.dept,
            base_salary=Decimal('60000.00'), is_active=True,
        )

    def test_payslip_net_equals_gross_minus_deductions(self):
        slip = Payslip.objects.create(
            company=self.company, employee=self.employee, period='2024-01',
            gross=Decimal('5000.00'), deductions=Decimal('1000.00'), net=Decimal('4000.00'),
        )
        self.assertEqual(slip.net, slip.gross - slip.deductions)
        self.assertTrue(slip.is_balanced)

    def test_attendance_worked_minutes(self):
        a = Attendance.objects.create(
            company=self.company, employee=self.employee, date=date(2024, 1, 15),
            clock_in=time(9, 0), clock_out=time(17, 30), status=Attendance.Status.PRESENT,
        )
        self.assertEqual(a.worked_minutes, 510)
        self.assertGreater(a.worked_minutes, 0)

    def test_attendance_without_clock_out_is_zero(self):
        a = Attendance.objects.create(
            company=self.company, employee=self.employee, date=date(2024, 1, 16),
        )
        self.assertEqual(a.worked_minutes, 0)

    def test_employee_on_leave_today(self):
        today = date.today()
        LeaveRequest.objects.create(
            company=self.company, employee=self.employee,
            start_date=today, end_date=today,
            leave_type=LeaveRequest.LeaveType.ANNUAL, status=LeaveRequest.Status.APPROVED,
        )
        self.assertTrue(self.employee.on_leave)