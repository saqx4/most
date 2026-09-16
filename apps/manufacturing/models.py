from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.core.models import CompanyScoped, TimeStampMixin, User

MONEY = dict(max_digits=14, decimal_places=2)
User = get_user_model()
ZERO = Decimal('0.00')


class BillOfMaterial(CompanyScoped):
    """Recipe: what to produce and what components it consumes."""
    number = models.CharField(max_length=30)
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='boms')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, null=True, blank=True, related_name='production_boms')
    is_active = models.BooleanField(default=True)
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='boms_created')

    class Meta:
        ordering = ['-id']
        constraints = [models.UniqueConstraint(fields=['company', 'product', 'number'], name='uniq_bom')]

    def __str__(self):
        return f'{self.number} - {self.product}'

    @property
    def components(self):
        return self.lines.select_related('component').all()


class BillOfMaterialLine(TimeStampMixin):
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.CASCADE, related_name='lines')
    component = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='bom_usages')
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    uom = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['id']

    def total_component_cost(self):
        return self.component.avg_cost * self.quantity


class WorkOrder(CompanyScoped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'
        CANCELLED = 'cancelled', 'Cancelled'

    number = models.CharField(max_length=30, editable=False, default='')
    bom = models.ForeignKey(BillOfMaterial, on_delete=models.PROTECT, related_name='work_orders')
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='work_orders')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, related_name='work_orders')
    quantity = models.DecimalField(**MONEY, default=Decimal('1.00'))
    created_at = None  # replaced by TimeStamp via CompanyScoped
    start_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_orders_created')
    finished_at = models.DateTimeField(null=True, blank=True)
    finished_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='work_orders_finished')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number

    @property
    def expected_material_cost(self):
        return sum(
            (l.component.avg_cost * l.quantity * self.quantity for l in self.bom.lines.all()), ZERO
        )


class WorkOrderMaterialRequirement(TimeStampMixin):
    """How much the work order actually needs / has been consumed."""
    order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='materials')
    component = models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='wo_materials')
    required = models.DecimalField(**MONEY, default=Decimal('1.00'))
    consumed = models.DecimalField(**MONEY, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.consumed}/{self.required} {self.component}'