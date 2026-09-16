from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.accounting.models import Account, TaxRate
from apps.core.models import CompanyScoped, TimeStampMixin, User

MONEY = dict(max_digits=14, decimal_places=2)
User = get_user_model()


class UnitOfMeasure(TimeStampMixin):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=12, blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.code or self.name


class Category(CompanyScoped):
    name = models.CharField(max_length=160)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_category_name'),
        ]

    def __str__(self):
        return self.name


class Warehouse(CompanyScoped):
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'code'], name='uniq_warehouse_code'),
        ]

    def __str__(self):
        return self.name


class Product(CompanyScoped):
    sku = models.CharField(max_length=60)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, null=True, blank=True, related_name='products')
    barcode = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    purchase_price = models.DecimalField(**MONEY, default=Decimal('0.00'))
    sale_price = models.DecimalField(**MONEY, default=Decimal('0.00'))
    income_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='products_income')
    cogs_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='products_cogs')
    expense_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='products_expense')
    is_service = models.BooleanField(default=False)
    is_sellable = models.BooleanField(default=True)
    is_tracked = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    reorder_point = models.DecimalField(**MONEY, default=Decimal('0.00'))
    avg_cost = models.DecimalField(**MONEY, default=Decimal('0.00'))
    can_backorder = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='products_created')

    class Meta:
        ordering = ['sku']
        constraints = [
            models.UniqueConstraint(fields=['company', 'sku'], name='uniq_product_sku'),
        ]

    def __str__(self):
        return f'{self.sku} - {self.name}'

    @property
    def on_hand(self):
        return self.stocks.aggregate(t=models.Sum('quantity'))['t'] or Decimal('0')

    @property
    def on_hand_by(self):
        return self.stocks

    def on_hand_in(self, warehouse=None):
        qs = self.stocks
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        return qs.aggregate(t=models.Sum('quantity'))['t'] or Decimal('0')

    @property
    def available(self):
        return self.on_hand

    def stock_value(self, warehouse=None):
        qs = self.stocks
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        rows = qs.aggregate(qty=models.Sum('quantity'), cost=models.Avg('avg_cost'))
        qty = rows['qty'] or Decimal('0')
        return qty * (rows['cost'] or Decimal('0'))


class StockLevel(CompanyScoped):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.DecimalField(**MONEY, default=Decimal('0.00'))
    avg_cost = models.DecimalField(**MONEY, default=Decimal('0.00'))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['company', 'product', 'warehouse'], name='uniq_stock_level'),
        ]

    def __str__(self):
        return f'{self.product} @ {self.warehouse}: {self.qty_value}'

    @property
    def value(self):
        return self.quantity * self.avg_cost

    def qty_value(self):
        return self.quantity


class StockMovement(CompanyScoped):
    class MovementType(models.TextChoices):
        PURCHASE_IN = 'po_in', 'Purchase Receipt'
        SALES_OUT = 'so_out', 'Delivery/Sales Out'
        TRANSFER = 'transfer', 'Inter-Warehouse Transfer'
        ADJUSTMENT = 'adjust', 'Adjustment'
        MANUFACTURE_IN = 'mf_in', 'Manufacturing Receipt'
        COMPONENT_OUT = 'mf_out', 'Manufacturing Consumption'
        RETURN_IN = 'ret_in', 'Sales Return In'
        RETURN_OUT = 'ret_out', 'Purchase Return Out'
        SALE = 'sale', 'Sale'  # legacy alias

    type = models.CharField(max_length=10, choices=MovementType.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='movements')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, null=True, blank=True, related_name='movements_to')
    quantity = models.DecimalField(**MONEY, default=Decimal('0.00'))
    unit_cost = models.DecimalField(**MONEY, default=Decimal('0.00'))
    date = models.DateTimeField(default=timezone.now)
    reference_type = models.CharField(max_length=100, blank=True)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    reference_number = models.CharField(max_length=60, blank=True)
    notes = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.get_type_display()} {self.quantity} {self.product} @ {self.warehouse}'


class StockTransfer(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        CANCELLED = 'cancelled', 'Cancelled'

    number = models.CharField(max_length=30, editable=False)
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='transfers_from')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='transfers_to')
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transfers')
    posted_at = models.DateTimeField(null=True, blank=True)
    reference_number = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.number}'

    @property
    def lines(self):
        return self.lines_rel.all()


class StockTransferLine(TimeStampMixin):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='lines_rel')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(**MONEY, default=Decimal('0.00'))

    def __str__(self):
        return f'{self.quantity} x {self.product}'


class StockAdjustment(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        CANCELLED = 'cancelled', 'Cancelled'

    number = models.CharField(max_length=30, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='adjustments')
    date = models.DateField(default=timezone.localdate)
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number


class StockAdjustmentLine(TimeStampMixin):
    adjustment = models.ForeignKey(StockAdjustment, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(**MONEY, default=Decimal('0.00'))
    reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f'{self.quantity} x {self.product}'