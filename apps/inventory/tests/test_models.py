from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company
from apps.accounting.models import Account
from apps.inventory.models import (
    Category, Product, StockLevel, StockMovement, UnitOfMeasure, Warehouse,
)


class UnitOfMeasureModelTest(TestCase):
    def test_create_uom(self):
        uom = UnitOfMeasure.objects.create(code='EA', name='Each', symbol='ea')
        self.assertEqual(str(uom), 'EA')


class CategoryModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')

    def test_create_category(self):
        cat = Category.objects.create(company=self.company, name='Parts')
        self.assertEqual(str(cat), 'Parts')


class WarehouseModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')

    def test_create_warehouse(self):
        wh = Warehouse.objects.create(company=self.company, name='Main WH')
        self.assertEqual(str(wh), 'Main WH')
        self.assertTrue(wh.is_active)


class ProductModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.product = Product.objects.create(
            company=self.company, sku='SKU001', name='Widget',
            purchase_price=Decimal('10.00'), sale_price=Decimal('25.00'),
        )

    def test_create_product(self):
        self.assertEqual(self.product.sku, 'SKU001')

    def test_str(self):
        self.assertEqual(str(self.product), 'SKU001 - Widget')

    def test_on_hand_empty(self):
        self.assertEqual(self.product.on_hand, Decimal('0'))

    def test_on_hand_with_stock(self):
        wh = Warehouse.objects.create(company=self.company, name='W1')
        StockLevel.objects.create(
            company=self.company, product=self.product,
            warehouse=wh, quantity=Decimal('50'), avg_cost=Decimal('10'),
        )
        self.assertEqual(self.product.on_hand, Decimal('50'))


class StockLevelModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.product = Product.objects.create(
            company=self.company, sku='P1', name='Part',
        )
        self.warehouse = Warehouse.objects.create(
            company=self.company, name='Main',
        )
        self.stock = StockLevel.objects.create(
            company=self.company, product=self.product,
            warehouse=self.warehouse, quantity=Decimal('100'),
            avg_cost=Decimal('5.00'),
        )

    def test_create_stock_level(self):
        self.assertEqual(self.stock.quantity, Decimal('100'))

    def test_value(self):
        self.assertEqual(self.stock.value, Decimal('500.00'))


class StockMovementModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.product = Product.objects.create(
            company=self.company, sku='P1', name='Part',
        )
        self.warehouse = Warehouse.objects.create(
            company=self.company, name='Main',
        )

    def test_create_movement(self):
        mv = StockMovement.objects.create(
            company=self.company, type=StockMovement.MovementType.PURCHASE_IN,
            product=self.product, warehouse=self.warehouse,
            quantity=Decimal('10'), unit_cost=Decimal('5.00'),
        )
        self.assertIn('Purchase Receipt', str(mv))
