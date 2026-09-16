from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company
from apps.inventory.models import Product, StockLevel, Warehouse
from apps.manufacturing.models import BillOfMaterial, BillOfMaterialLine, WorkOrder


class ManufacturingModelTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Factory Co')
        self.wh = Warehouse.objects.create(company=self.company, name='Main')
        self.raw = Product.objects.create(
            company=self.company, sku='RAW-1', name='Raw bar',
            purchase_price=Decimal('4.00'), avg_cost=Decimal('4.00'),
        )
        self.fin = Product.objects.create(
            company=self.company, sku='FIN-1', name='Widget',
            sale_price=Decimal('10.00'), reorder_point=Decimal('5.00'),
        )

    def test_product_reorder_logic(self):
        StockLevel.objects.create(
            company=self.company, product=self.fin, warehouse=self.wh, quantity=Decimal('3.00'),
        )
        self.assertLessEqual(self.fin.on_hand, self.fin.reorder_point)

    def test_bom_expected_material_cost(self):
        bom = BillOfMaterial.objects.create(
            company=self.company, product=self.fin, number='BOM-1', quantity=Decimal('1.00'),
        )
        BillOfMaterialLine.objects.create(bom=bom, component=self.raw, quantity=Decimal('2.00'))
        wo = WorkOrder.objects.create(
            company=self.company, bom=bom, product=self.fin,
            warehouse=self.wh, quantity=Decimal('3.00'),
        )
        self.assertEqual(wo.expected_material_cost, Decimal('24.00'))
        self.assertEqual(wo.bom.components.count(), 1)

    def test_work_order_status_defaults_to_draft(self):
        bom = BillOfMaterial.objects.create(company=self.company, product=self.fin, number='BOM-2')
        wo = WorkOrder.objects.create(
            company=self.company, bom=bom, product=self.fin,
            warehouse=self.wh, quantity=Decimal('1.00'),
        )
        self.assertEqual(wo.status, WorkOrder.Status.DRAFT)
        self.assertTrue(wo.number)