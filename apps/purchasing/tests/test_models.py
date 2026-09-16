from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company
from apps.inventory.models import Product
from apps.purchasing.models import PurchaseOrder, Supplier, SupplierBill


class SupplierModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.supplier = Supplier.objects.create(
            company=self.company, name='Vendor A',
        )

    def test_create_supplier(self):
        self.assertEqual(self.supplier.name, 'Vendor A')
        self.assertTrue(self.supplier.is_active)

    def test_str(self):
        self.assertEqual(str(self.supplier), 'Vendor A')


class PurchaseOrderModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.supplier = Supplier.objects.create(
            company=self.company, name='V1',
        )
        self.po = PurchaseOrder.objects.create(
            company=self.company, supplier=self.supplier,
            number='PO-0001',
        )

    def test_create_po(self):
        self.assertEqual(self.po.status, 'draft')

    def test_str(self):
        self.assertEqual(str(self.po), 'PO-0001')


class SupplierBillModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.supplier = Supplier.objects.create(
            company=self.company, name='V1',
        )
        self.bill = SupplierBill.objects.create(
            company=self.company, supplier=self.supplier,
            number='BILL-0001',
        )

    def test_create_bill(self):
        self.assertEqual(self.bill.status, SupplierBill.Status.DRAFT)

    def test_str(self):
        self.assertEqual(str(self.bill), 'BILL-0001')
