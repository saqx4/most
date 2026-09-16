from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company
from apps.purchasing.models import PurchaseOrder, Supplier, SupplierBill

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='TestCo')

    def test_create_supplier(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        self.assertEqual(supplier.name, 'Widget Supply Co')
        self.assertTrue(supplier.is_active)

    def test_str_supplier(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        self.assertEqual(str(supplier), 'Widget Supply Co')

    def test_supplier_defaults(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        self.assertEqual(supplier.email, '')
        self.assertEqual(supplier.phone, '')
        self.assertEqual(supplier.website, '')
        self.assertTrue(supplier.is_payable)

    def test_create_purchase_order(self):
        from apps.inventory.models import Warehouse
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        warehouse = Warehouse.objects.create(
            company=self.company, name='Main WH',
        )
        po = PurchaseOrder.objects.create(
            company=self.company, supplier=supplier,
            number='PO-001',
            status='draft',
        )
        self.assertEqual(po.number, 'PO-001')

    def test_str_purchase_order(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        po = PurchaseOrder.objects.create(
            company=self.company, supplier=supplier,
            number='PO-001',
        )
        self.assertEqual(str(po), 'PO-001')

    def test_create_supplier_bill(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        bill = SupplierBill.objects.create(
            company=self.company, supplier=supplier,
            number='BILL-001',
            status='draft',
        )
        self.assertEqual(bill.number, 'BILL-001')

    def test_str_supplier_bill(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        bill = SupplierBill.objects.create(
            company=self.company, supplier=supplier,
            number='BILL-001',
        )
        self.assertEqual(str(bill), 'BILL-001')

    def test_bill_defaults(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        bill = SupplierBill.objects.create(
            company=self.company, supplier=supplier,
        )
        self.assertEqual(bill.status, 'draft')
        self.assertEqual(bill.memo, '')


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testadmin', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        self.client.login(username='testadmin', password='testpass123')
        self.company = Company.objects.create(name='TestCo', is_default=True)

    def test_supplier_list(self):
        resp = self.client.get(reverse('purchasing:supplier_list'))
        self.assertEqual(resp.status_code, 200)

    def test_supplier_create(self):
        resp = self.client.get(reverse('purchasing:supplier_create'))
        self.assertEqual(resp.status_code, 200)

    def test_po_list(self):
        resp = self.client.get(reverse('purchasing:po_list'))
        self.assertEqual(resp.status_code, 200)

    def test_bill_list(self):
        resp = self.client.get(reverse('purchasing:bill_list'))
        self.assertEqual(resp.status_code, 200)

    def test_supplier_delete(self):
        supplier = Supplier.objects.create(
            company=self.company, name='Widget Supply Co',
        )
        resp = self.client.post(reverse('purchasing:supplier_delete', args=[supplier.pk]))
        self.assertEqual(resp.status_code, 302)
