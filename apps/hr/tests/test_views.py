from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User
from apps.hr.models import Department, Employee


class HRViewTestMixin:
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')
        self.dept = Department.objects.create(
            company=self.company, name='Engineering', code='ENG',
        )
        self.employee = Employee.objects.create(
            company=self.company, employee_code='EMP001',
            first_name='John', last_name='Doe',
            department=self.dept,
        )


class HRDashboardTest(HRViewTestMixin, TestCase):
    def test_dashboard_200(self):
        response = self.client.get(reverse('hr:dashboard'))
        self.assertEqual(response.status_code, 200)


class EmployeeListTest(HRViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('hr:employee_list'))
        self.assertEqual(response.status_code, 200)


class EmployeeDetailTest(HRViewTestMixin, TestCase):
    def test_detail_200(self):
        response = self.client.get(
            reverse('hr:employee_detail', args=[self.employee.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_404(self):
        response = self.client.get(
            reverse('hr:employee_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)


class EmployeeCreateTest(HRViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('hr:employee_create'))
        self.assertEqual(response.status_code, 200)


class EmployeeDeleteTest(HRViewTestMixin, TestCase):
    def test_delete_redirects(self):
        response = self.client.post(
            reverse('hr:employee_delete', args=[self.employee.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())


class DepartmentListTest(HRViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('hr:department_list'))
        self.assertEqual(response.status_code, 200)


class AttendanceListTest(HRViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('hr:attendance_list'))
        self.assertEqual(response.status_code, 200)


class LeaveListTest(HRViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('hr:leave_list'))
        self.assertEqual(response.status_code, 200)


class PayslipListTest(HRViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('hr:payslip_list'))
        self.assertEqual(response.status_code, 200)


class PayslipCreateTest(HRViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('hr:payslip_create'))
        self.assertEqual(response.status_code, 200)
