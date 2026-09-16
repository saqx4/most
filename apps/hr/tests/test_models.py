from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company
from apps.hr.models import Attendance, Department, Employee, LeaveRequest, Payslip


class DepartmentModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')

    def test_create_department(self):
        dept = Department.objects.create(
            company=self.company, name='Engineering', code='ENG',
        )
        self.assertEqual(dept.name, 'Engineering')
        self.assertTrue(dept.is_active)

    def test_str(self):
        dept = Department.objects.create(
            company=self.company, name='Sales', code='SALES',
        )
        self.assertEqual(str(dept), 'Sales')


class EmployeeModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.dept = Department.objects.create(
            company=self.company, name='Engineering', code='ENG',
        )
        self.employee = Employee.objects.create(
            company=self.company, employee_code='EMP001',
            first_name='John', last_name='Doe',
            department=self.dept, base_salary=Decimal('5000.00'),
        )

    def test_create_employee(self):
        self.assertEqual(self.employee.employee_code, 'EMP001')
        self.assertTrue(self.employee.is_active)

    def test_str(self):
        self.assertIn('EMP001', str(self.employee))

    def test_full_name(self):
        self.assertEqual(self.employee.full_name, 'John Doe')


class AttendanceModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.employee = Employee.objects.create(
            company=self.company, employee_code='E1',
            first_name='A', last_name='B',
        )

    def test_create_attendance(self):
        att = Attendance.objects.create(
            company=self.company, employee=self.employee,
            status=Attendance.Status.PRESENT,
        )
        self.assertEqual(att.status, 'present')

    def test_worked_minutes_no_times(self):
        att = Attendance.objects.create(
            company=self.company, employee=self.employee,
            status=Attendance.Status.PRESENT,
        )
        self.assertEqual(att.worked_minutes, 0)


class LeaveRequestModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.employee = Employee.objects.create(
            company=self.company, employee_code='E1',
            first_name='A', last_name='B',
        )

    def test_create_leave_request(self):
        lr = LeaveRequest.objects.create(
            company=self.company, employee=self.employee,
            start_date='2025-01-01', end_date='2025-01-05',
        )
        self.assertEqual(lr.status, LeaveRequest.Status.PENDING)

    def test_days(self):
        lr = LeaveRequest.objects.create(
            company=self.company, employee=self.employee,
            start_date='2025-01-01', end_date='2025-01-05',
        )
        self.assertEqual(lr.days, 5)


class PayslipModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.employee = Employee.objects.create(
            company=self.company, employee_code='E1',
            first_name='A', last_name='B',
        )

    def test_create_payslip(self):
        ps = Payslip.objects.create(
            company=self.company, employee=self.employee,
            period='2025-01', gross=Decimal('5000'),
            deductions=Decimal('1000'), net=Decimal('4000'),
        )
        self.assertEqual(ps.status, Payslip.Status.DRAFT)

    def test_is_balanced(self):
        ps = Payslip.objects.create(
            company=self.company, employee=self.employee,
            period='2025-01', gross=Decimal('5000'),
            deductions=Decimal('1000'), net=Decimal('4000'),
        )
        self.assertTrue(ps.is_balanced)

    def test_is_not_balanced(self):
        ps = Payslip.objects.create(
            company=self.company, employee=self.employee,
            period='2025-02', gross=Decimal('5000'),
            deductions=Decimal('1000'), net=Decimal('3500'),
        )
        self.assertFalse(ps.is_balanced)
