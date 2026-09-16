from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User
from apps.purchasing.models import PurchaseOrder, Supplier, SupplierBill


class PurchasingViewTestMixin:
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')
        self.supplier = Supplier.objects.create(
            company=self.company, name='Vendor',
        )


class PurchasingDashboardTest(PurchasingViewTestMixin, TestCase):
    def test_dashboard_200(self):
        response = self.client.get(reverse('purchasing:dashboard'))
        self.assertEqual(response.status_code, 200)


class SupplierListTest(PurchasingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('purchasing:supplier_list'))
        self.assertEqual(response.status_code, 200)


class SupplierDetailTest(PurchasingViewTestMixin, TestCase):
    def test_detail_200(self):
        response = self.client.get(
            reverse('purchasing:supplier_detail', args=[self.supplier.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_404(self):
        response = self.client.get(
            reverse('purchasing:supplier_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)


class SupplierCreateTest(PurchasingViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('purchasing:supplier_create'))
        self.assertEqual(response.status_code, 200)


class SupplierDeleteTest(PurchasingViewTestMixin, TestCase):
    def test_delete_redirects(self):
        response = self.client.post(
            reverse('purchasing:supplier_delete', args=[self.supplier.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Supplier.objects.filter(pk=self.supplier.pk).exists())


class POListTest(PurchasingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('purchasing:po_list'))
        self.assertEqual(response.status_code, 200)


class PODetailTest(PurchasingViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.po = PurchaseOrder.objects.create(
            company=self.company, supplier=self.supplier,
            number='PO-0001',
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('purchasing:po_detail', args=[self.po.pk])
        )
        self.assertEqual(response.status_code, 200)


class POCreateTest(PurchasingViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('purchasing:po_create'))
        self.assertEqual(response.status_code, 200)


class BillListTest(PurchasingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('purchasing:bill_list'))
        self.assertEqual(response.status_code, 200)


class BillDetailTest(PurchasingViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.bill = SupplierBill.objects.create(
            company=self.company, supplier=self.supplier,
            number='BILL-0001',
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('purchasing:bill_detail', args=[self.bill.pk])
        )
        self.assertEqual(response.status_code, 200)


class BillCreateTest(PurchasingViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('purchasing:bill_create'))
        self.assertEqual(response.status_code, 200)


class PaymentListTest(PurchasingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('purchasing:payment_list'))
        self.assertEqual(response.status_code, 200)
