from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company
from apps.manufacturing.models import BillOfMaterial, WorkOrder

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='TestCo')

    def _create_product(self, sku='SKU-001', name='Widget'):
        from apps.inventory.models import Product
        return Product.objects.create(
            company=self.company, sku=sku, name=name,
        )

    def _create_warehouse(self):
        from apps.inventory.models import Warehouse
        return Warehouse.objects.create(
            company=self.company, name='Main WH',
        )

    def test_create_bom(self):
        product = self._create_product()
        bom = BillOfMaterial.objects.create(
            company=self.company, product=product,
            number='BOM-001', quantity=Decimal('1.00'),
        )
        self.assertEqual(bom.number, 'BOM-001')
        self.assertTrue(bom.is_active)

    def test_str_bom(self):
        product = self._create_product()
        bom = BillOfMaterial.objects.create(
            company=self.company, product=product,
            number='BOM-001',
        )
        self.assertIn('BOM-001', str(bom))
        self.assertIn('Widget', str(bom))

    def test_bom_defaults(self):
        product = self._create_product()
        bom = BillOfMaterial.objects.create(
            company=self.company, product=product,
            number='BOM-001',
        )
        self.assertTrue(bom.is_active)
        self.assertEqual(bom.quantity, Decimal('1.00'))
        self.assertEqual(bom.notes, '')

    def test_create_work_order(self):
        product = self._create_product()
        bom = BillOfMaterial.objects.create(
            company=self.company, product=product,
            number='BOM-001',
        )
        warehouse = self._create_warehouse()
        wo = WorkOrder.objects.create(
            company=self.company, product=product,
            bom=bom, warehouse=warehouse,
            number='WO-001', quantity=Decimal('1.00'),
        )
        self.assertEqual(wo.number, 'WO-001')
        self.assertEqual(wo.status, 'draft')

    def test_str_work_order(self):
        product = self._create_product()
        bom = BillOfMaterial.objects.create(
            company=self.company, product=product,
            number='BOM-001',
        )
        warehouse = self._create_warehouse()
        wo = WorkOrder.objects.create(
            company=self.company, product=product,
            bom=bom, warehouse=warehouse,
            number='WO-001',
        )
        self.assertEqual(str(wo), 'WO-001')

    def test_work_order_defaults(self):
        product = self._create_product()
        bom = BillOfMaterial.objects.create(
            company=self.company, product=product,
            number='BOM-001',
        )
        warehouse = self._create_warehouse()
        wo = WorkOrder.objects.create(
            company=self.company, product=product,
            bom=bom, warehouse=warehouse,
        )
        self.assertEqual(wo.status, 'draft')
        self.assertEqual(wo.notes, '')
        self.assertEqual(wo.quantity, Decimal('1.00'))


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testadmin', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        self.client.login(username='testadmin', password='testpass123')
        self.company = Company.objects.create(name='TestCo', is_default=True)

    def test_bom_list(self):
        resp = self.client.get(reverse('manufacturing:bom_list'))
        self.assertEqual(resp.status_code, 200)

    def test_bom_create(self):
        resp = self.client.get(reverse('manufacturing:bom_create'))
        self.assertEqual(resp.status_code, 200)

    def test_workorder_list(self):
        resp = self.client.get(reverse('manufacturing:workorder_list'))
        self.assertEqual(resp.status_code, 200)
