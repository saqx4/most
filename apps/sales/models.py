from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.accounting.models import Account, Currency, TaxRate
from apps.core.models import CompanyScoped, TimeStampMixin, User

MONEY = dict(max_digits=14, decimal_places=2)
User = get_user_model()


# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------
class PipelineStage(CompanyScoped):
    name = models.CharField(max_length=100)
    position = models.PositiveSmallIntegerField(default=0)
    win_probability = models.PositiveSmallIntegerField(default=0)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_pipeline_stage'),
        ]

    def __str__(self):
        return self.name


class Lead(CompanyScoped):
    company_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    source = models.CharField(max_length=60, blank=True)
    stage = models.ForeignKey(PipelineStage, on_delete=models.PROTECT, null=True, blank=True, related_name='leads')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads_owned')
    expected_revenue = models.DecimalField(**MONEY, default=Decimal('0.00'))
    probability = models.PositiveSmallIntegerField(default=10)
    next_action_date = models.DateField(null=True, blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.company_name

    @property
    def value(self):
        return self.expected_revenue * (self.probability / Decimal('100'))


class Customer(CompanyScoped):
    name = models.CharField(max_length=200)
    CLIENT_TYPE_CHOICES = [
        ('individual', 'Individual / فردي'),
        ('commercial', 'Commercial / تجاري'),
    ]
    client_type = models.CharField(max_length=15, choices=CLIENT_TYPE_CHOICES, default='commercial')
    commercial_name = models.CharField(max_length=200, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    mobile = models.CharField(max_length=60, blank=True)
    commercial_reg = models.CharField(max_length=100, blank=True)  # سجل تجاري
    street1 = models.CharField(max_length=200, blank=True)
    street2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Secondary shipping address
    shipping_street1 = models.CharField(max_length=200, blank=True)
    shipping_street2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_postal_code = models.CharField(max_length=30, blank=True)
    shipping_country = models.CharField(max_length=100, blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    website = models.URLField(blank=True)
    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name='customer_balances')
    payment_term = models.ForeignKey('accounting.PaymentTerm', on_delete=models.PROTECT, null=True, blank=True, related_name='customers')
    credit_limit = models.DecimalField(**MONEY, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    ar_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='customers_ar')
    is_customer = models.BooleanField(default=True)
    is_supplier = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customers_created')

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='uniq_customer_name'),
        ]

    def __str__(self):
        return self.name

    @property
    def balance(self):
        return sum(
            i.total - i.paid_total
            for i in self.ar_invoices.filter(status__in=['draft', 'posted'])
        )


class SalesDocumentMixin(TimeStampMixin):
    status = models.CharField(max_length=12, default='draft')

    class Meta:
        abstract = True

    @property
    def total(self):
        from apps.sales.services import document_total
        return document_total(self.lines.all())

    @property
    def is_draft(self):
        return self.status == 'draft'


class SalesOrder(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        CONFIRMED = 'confirmed', 'Confirmed'
        FULFILLED = 'fulfilled', 'Fulfilled'
        CANCELLED = 'cancelled', 'Cancelled'

    number = models.CharField(max_length=30, editable=False, blank=True)
    order_type = models.CharField(max_length=10, default='order')  # order | quotation | return
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, related_name='sales_orders')
    order_date = models.DateField(default=timezone.localdate)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    salesperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True, related_name='sales_orders')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders_created')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal('1.000000'), help_text='Exchange rate to base currency')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number or f'SO#{self.pk}'

    @property
    def total(self):
        from apps.sales.services import document_total
        return document_total(self.lines.all())


class SalesOrderLine(TimeStampMixin):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='sales_lines')
    description = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    price = models.DecimalField(**MONEY, default=Decimal('0.00'))
    discount_percent = models.DecimalField(**MONEY, default=Decimal('0.00'))
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} x {self.product}'

    def line_total(self, tax=False):
        return line_amount(self.price, self.quantity, self.discount_percent, tax)

    @property
    def delivered_qty(self):
        from apps.inventory.models import Product, StockMovement
        total = StockMovement.objects.filter(
            product=self.product, type=StockMovement.MovementType.SALES_OUT,
            reference_type='SALES_DELIVERY', reference_id__in=self.order.deliveries.values_list('id', flat=True),
        ).aggregate(t=models.Sum('quantity'))['t']
        return total or Decimal('0')


class DeliveryNote(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        CANCELLED = 'cancelled', 'Cancelled'

    number = models.CharField(max_length=30, editable=False)
    order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='deliveries', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='deliveries')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, related_name='deliveries')
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number


class DeliveryNoteLine(TimeStampMixin):
    delivery = models.ForeignKey(DeliveryNote, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))

    class Meta:
        ordering = ['id']


class SalesInvoice(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'

    number = models.CharField(max_length=30, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='ar_invoices')
    order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, null=True, blank=True, related_name='invoices')
    invoice_date = models.DateField(default=timezone.localdate)
    issue_date = models.DateField(default=timezone.localdate, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    payment_terms_days = models.PositiveIntegerField(default=0, help_text='Payment terms in days')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True)
    salesperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_invoices')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    # Daftra Header & Layout
    template_design = models.CharField(max_length=50, default='default', blank=True)

    # Shipping Details (بيانات الشحن ومصاريف الشحن)
    has_shipping = models.BooleanField(default=False)
    shipping_recipient = models.CharField(max_length=150, blank=True)
    shipping_address_text = models.TextField(blank=True)
    shipping_amount = models.DecimalField(**MONEY, default=Decimal('0.00'))

    # Global Discounts & Adjustments (خصم كلي وتسويات)
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount / مبلغ ثابت'),
        ('percent', 'Percentage / نسبة مئوية'),
    ]
    global_discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='fixed')
    global_discount_value = models.DecimalField(**MONEY, default=Decimal('0.00'))
    adjustment_label = models.CharField(max_length=100, blank=True, default='')
    adjustment_value = models.DecimalField(**MONEY, default=Decimal('0.00'))

    # Paid Upfront (مدفوع بالفعل)
    is_paid_upfront = models.BooleanField(default=False)
    upfront_payment_amount = models.DecimalField(**MONEY, default=Decimal('0.00'))
    upfront_payment_method = models.CharField(max_length=30, blank=True, default='cash')
    upfront_payment_reference = models.CharField(max_length=100, blank=True)

    memo = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal('1.000000'), help_text='Exchange rate to base currency')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number

    @property
    def total(self):
        from apps.sales.services import document_total
        return document_total(self.lines.all(), invoice=self)

    @property
    def paid_total(self):
        return self.allocations.aggregate(t=models.Sum('allocated'))['t'] or Decimal('0')

    @property
    def amount_due(self):
        return self.total - self.paid_total


class SalesInvoiceLine(TimeStampMixin):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage (%)'),
        ('fixed', 'Fixed Amount'),
    ]
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='invoice_lines')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_lines')
    salesperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    price = models.DecimalField(**MONEY, default=Decimal('0.00'))
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    discount_percent = models.DecimalField(**MONEY, default=Decimal('0.00'))
    discount_amount = models.DecimalField(**MONEY, default=Decimal('0.00'))
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True, related_name='invoice_lines_tax1')
    tax2 = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True, related_name='invoice_lines_tax2')

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        gross = self.price * self.quantity
        if self.discount_type == 'fixed':
            disc = self.discount_amount
        else:
            disc = gross * (self.discount_percent / Decimal('100.00'))
        net = max(Decimal('0.00'), gross - disc)
        tax_add = Decimal('0.00')
        if self.tax:
            tax_add += net * (self.tax.rate / Decimal('100.00'))
        if self.tax2:
            tax_add += net * (self.tax2.rate / Decimal('100.00'))
        return net + tax_add


class CustomerPayment(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        RECEIVED = 'received', 'Received'
        VOID = 'void', 'Void'

    number = models.CharField(max_length=30, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='payments')
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


class ARPaymentAllocation(TimeStampMixin):
    """Matches a customer payment against open invoices (applied to oldest first)."""
    payment = models.ForeignKey(CustomerPayment, on_delete=models.CASCADE, related_name='allocations')
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, related_name='allocations')
    allocated = models.DecimalField(**MONEY, default=Decimal('0.00'))


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------
class SalesQuote(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED = 'expired', 'Expired'

    number = models.CharField(max_length=30, editable=False, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='quotes')
    quote_date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField(null=True, blank=True)
    payment_terms_days = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    salesperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_quotes')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='quotes')

    # Global Discounts & Shipping
    has_shipping = models.BooleanField(default=False)
    shipping_recipient = models.CharField(max_length=150, blank=True)
    shipping_address_text = models.TextField(blank=True)
    shipping_amount = models.DecimalField(**MONEY, default=Decimal('0.00'))
    global_discount_type = models.CharField(max_length=10, choices=SalesInvoice.DISCOUNT_TYPE_CHOICES, default='fixed')
    global_discount_value = models.DecimalField(**MONEY, default=Decimal('0.00'))
    adjustment_label = models.CharField(max_length=100, blank=True, default='')
    adjustment_value = models.DecimalField(**MONEY, default=Decimal('0.00'))

    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    converted_to_order = models.ForeignKey(SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='converted_quotes')
    exchange_rate = models.DecimalField(max_digits=14, decimal_places=6, default=Decimal('1.000000'), help_text='Exchange rate to base currency')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number or f'QOT#{self.pk}'

    @property
    def total(self):
        from apps.sales.services import document_total
        return document_total(self.lines.all(), invoice=self)


class SalesQuoteLine(TimeStampMixin):
    quote = models.ForeignKey(SalesQuote, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='quote_lines')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='quote_lines')
    description = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    price = models.DecimalField(**MONEY, default=Decimal('0.00'))
    discount_type = models.CharField(max_length=10, choices=SalesInvoiceLine.DISCOUNT_TYPE_CHOICES, default='percent')
    discount_percent = models.DecimalField(**MONEY, default=Decimal('0.00'))
    discount_amount = models.DecimalField(**MONEY, default=Decimal('0.00'))
    tax = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True, related_name='quote_lines_tax1')
    tax2 = models.ForeignKey(TaxRate, on_delete=models.PROTECT, null=True, blank=True, related_name='quote_lines_tax2')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} x {self.product}'

    @property
    def line_total(self):
        gross = self.price * self.quantity
        if self.discount_type == 'fixed':
            disc = self.discount_amount
        else:
            disc = gross * (self.discount_percent / Decimal('100.00'))
        net = max(Decimal('0.00'), gross - disc)
        tax_add = Decimal('0.00')
        if self.tax:
            tax_add += net * (self.tax.rate / Decimal('100.00'))
        if self.tax2:
            tax_add += net * (self.tax2.rate / Decimal('100.00'))
        return net + tax_add


# ---------------------------------------------------------------------------
# Credit Notes (Returned Invoices)
# ---------------------------------------------------------------------------
class CreditNote(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        POSTED = 'posted', 'Posted'
        VOID = 'void', 'Void'

    number = models.CharField(max_length=30, editable=False, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='credit_notes')
    original_invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, null=True, blank=True, related_name='credit_notes')
    credit_date = models.DateField(default=timezone.localdate)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number or f'CN#{self.pk}'

    @property
    def total(self):
        from apps.sales.services import document_total
        return document_total(self.lines.all())


class CreditNoteLine(TimeStampMixin):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='credit_note_lines')
    description = models.CharField(max_length=200, blank=True)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    price = models.DecimalField(**MONEY, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return line_amount(self.price, self.quantity)


# ---------------------------------------------------------------------------
# Periodic (Recurring) Invoices
# ---------------------------------------------------------------------------
class PeriodicInvoice(CompanyScoped):
    class Frequency(models.TextChoices):
        WEEKLY = 'weekly', 'Weekly'
        BIWEEKLY = 'biweekly', 'Bi-weekly'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUALLY = 'annually', 'Annually'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'

    number = models.CharField(max_length=30, editable=False, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='periodic_invoices')
    frequency = models.CharField(max_length=12, choices=Frequency.choices, default=Frequency.MONTHLY)
    next_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    template_invoice = models.ForeignKey(SalesInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='periodic_templates')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    last_generated = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['next_date']

    def __str__(self):
        return self.number or f'PER#{self.pk}'


# ---------------------------------------------------------------------------
# Sales Settings (singleton per company)
# ---------------------------------------------------------------------------
class SalesSettings(CompanyScoped):
    default_payment_term = models.ForeignKey('accounting.PaymentTerm', on_delete=models.SET_NULL, null=True, blank=True)
    default_tax = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_prefix = models.CharField(max_length=10, default='INV')
    quote_prefix = models.CharField(max_length=10, default='QOT')
    credit_note_prefix = models.CharField(max_length=10, default='CN')
    order_prefix = models.CharField(max_length=10, default='SO')
    receipt_prefix = models.CharField(max_length=10, default='RCPT')

    # Daftra Numbering Settings Parity (إعدادات الترقيم المتسلسل)
    NUMBERING_FORMAT_CHOICES = [
        ('prefix_num', 'بادئة ورقم متسلسل (مثال: INV-0001)'),
        ('prefix_year_num', 'بادئة وسنة ورقم (مثال: INV-2026-0001)'),
        ('prefix_month_num', 'بادئة وشهر وسنة ورقم (مثال: INV-2026-09-0001)'),
    ]
    numbering_format = models.CharField(max_length=30, choices=NUMBERING_FORMAT_CHOICES, default='prefix_num')
    number_padding = models.PositiveSmallIntegerField(default=4, help_text='عدد خانات الرقم (مثال: 4 خانات تعطي 0001)')
    reset_sequence_yearly = models.BooleanField(default=False, help_text='إعادة تصفير الترقيم سنوياً')
    next_invoice_number = models.PositiveIntegerField(default=1, help_text='رقم الفاتورة التالي')

    default_notes = models.TextField(blank=True)
    default_terms = models.TextField(blank=True)
    auto_post_invoices = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Sales Settings'
        verbose_name_plural = 'Sales Settings'

    def __str__(self):
        return f'Sales Settings - {self.company}'


# --- shared helpers ----------------------------------------------------------
def line_amount(price, quantity, discount_percent=Decimal('0.00'), with_tax=False):
    subtotal = price * quantity
    if discount_percent:
        subtotal = subtotal - (subtotal * (discount_percent / Decimal('100')))
    return subtotal