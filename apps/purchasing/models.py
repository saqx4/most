from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.accounting.models import Account, Currency, TaxRate
from apps.core.models import CompanyScoped, NumberSequence, TimeStampMixin, User

MONEY = dict(max_digits=14, decimal_places=2)
User = get_user_model()


class Supplier(CompanyScoped):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name='supplier_currencies')
    payment_term = models.ForeignKey('accounting.PaymentTerm', on_delete=models.PROTECT, null=True, blank=True, related_name='suppliers')
    ap_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='suppliers_ap')
    is_active = models.BooleanField(default=True)
    is_payable = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [models.UniqueConstraint(fields=['company', 'name'], name='uniq_supplier_name')]

    def __str__(self):
        return self.name


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    CONFIRMED = 'confirmed', 'Confirmed'
    RECEIVED = 'received', 'Received'
    PARTIAL = 'partial', 'Partially Received'
    CANCELLED = 'cancelled', 'Cancelled'
    CLOSED = 'closed', 'Closed'


class PurchaseOrder(CompanyScoped):
    class Meta:
        ordering = ['-id']

    number = models.CharField(max_length=30, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    order_date = models.DateField(default=timezone.localdate)
    expected_delivery = models.DateField(null=True, blank=True)
    delivery_address = models.TextField(blank=True)
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True, related_name='purchase_orders')
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=10, choices=PurchaseOrderStatus.choices, default=PurchaseOrderStatus.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders_created')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders_confirmed')
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.number

    def _next_line_number(self):
        last = self.lines.aggregate(m=models.Max('id'))['m'] or 0
        return last

    @property
    def total(self):
        total = sum(line.subtotal for line in self.lines.all())
        if self.tax:
            total += total * (self.tax.rate / Decimal('100.00'))
        return total

    @property
    def received_total(self):
        return sum(line.received_value() for line in self.lines.all())


class PurchaseOrderLine(TimeStampMixin):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='purchase_lines')
    description = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    quantity_received = models.DecimalField(**MONEY, default=Decimal('0.00'))
    unit_price = models.DecimalField(**MONEY, default=Decimal('0.00'))
    discount_percent = models.DecimalField(**MONEY, default=Decimal('0.00'))
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} x {self.product}'

    def subtotal(self):
        return (self.unit_price * self.quantity) * (Decimal('1.00') - self.discount_percent / Decimal('100.00'))

    def received_value(self):
        if not self.quantity:
            return Decimal('0.00')
        return self.subtotal() * (self.quantity_received / self.quantity)


class GoodsReceipt(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        CANCELLED = 'cancelled', 'Cancelled'

    number = models.CharField(max_length=30, editable=False)
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='goods_receipts', null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='goods_receipts')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, related_name='goods_receipts')
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number


class GoodsReceiptLine(TimeStampMixin):
    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='receipt_lines')
    order_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.SET_NULL, null=True, blank=True, related_name='receipts')
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    unit_cost = models.DecimalField(**MONEY, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']


class SupplierBill(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'

    number = models.CharField(max_length=30, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='bills')
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='bills', null=True, blank=True)
    bill_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    memo = models.TextField(blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number

    @property
    def total(self):
        base = sum(line.subtotal() for line in self.lines.all())
        if self.tax:
            base += base * (self.tax.rate / Decimal('100.00'))
        return base

    @property
    def paid_total(self):
        from apps.accounting.models import Currency as Cur
        allocs = self.bill_payments.aggregate(t=models.Sum('allocated'))['t'] or Decimal('0.00')
        return allocs

    @property
    def __balance(self):
        return self.total - self.paid_total


class SupplierBillLine(TimeStampMixin):
    bill = models.ForeignKey(SupplierBill, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='bill_lines')
    description = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    unit_price = models.DecimalField(**MONEY, default=Decimal('0.00'))
    discount_percent = models.DecimalField(**MONEY, default=Decimal('0.00'))
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def subtotal(self):
        return (self.unit_price * self.quantity) * (Decimal('1.00') - self.discount_percent / Decimal('100.00'))


class SupplierPayment(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        RECEIVED = 'received', 'Received'  # sent to supplier
        VOID = 'void', 'Void'

    number = models.CharField(max_length=30, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='payments')
    date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(**MONEY, default=Decimal('0.00'))
    method = models.CharField(max_length=20, default='bank')  # bank | cash | card | check | other
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number


class APPaymentAllocation(TimeStampMixin):
    payment = models.ForeignKey(SupplierPayment, on_delete=models.CASCADE, related_name='allocations')
    bill = models.ForeignKey(SupplierBill, on_delete=models.PROTECT, related_name='payments_allocations')
    allocated = models.DecimalField(**MONEY, default=Decimal('0.00'))
