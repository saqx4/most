"""Manufacturing business logic."""
from decimal import Decimal

from django.db import transaction


def calculate_bom_cost(bom):
    """Calculate total BOM cost from component costs."""
    total = Decimal('0.00')
    for line in bom.lines.all():
        total += line.component.purchase_price * line.quantity
    return total


def start_work_order(work_order):
    """Start a work order: validate stock availability, reserve components."""
    for line in work_order.bom.lines.all():
        from apps.inventory.models import StockLevel
        stock = StockLevel.objects.filter(
            product=line.component,
            warehouse=work_order.bom.warehouse
        ).first()
        available = stock.quantity if stock else 0
        if available < line.quantity * work_order.quantity:
            raise ValueError(
                f'Insufficient stock for {line.component.name}: '
                f'need {line.quantity * work_order.quantity}, have {available}'
            )
    work_order.status = 'in_progress'
    work_order.save()


def complete_work_order(work_order):
    """Complete a work order: consume components, produce finished goods."""
    from apps.inventory.models import StockMovement, StockLevel
    with transaction.atomic():
        for line in work_order.bom.lines.all():
            qty = line.quantity * work_order.quantity
            StockMovement.objects.create(
                product=line.component,
                warehouse=work_order.bom.warehouse,
                type='out',
                quantity=-qty,
                unit_cost=line.component.purchase_price,
                reference_number=work_order.order_number,
            )
            sl, _ = StockLevel.objects.get_or_create(
                product=line.component,
                warehouse=work_order.bom.warehouse,
                defaults={'quantity': 0}
            )
            sl.quantity -= qty
            sl.save()

        qty = work_order.quantity
        StockMovement.objects.create(
            product=work_order.bom.product,
            warehouse=work_order.bom.warehouse,
            type='in',
            quantity=qty,
            unit_cost=calculate_bom_cost(work_order.bom),
            reference_number=work_order.order_number,
        )
        sl, _ = StockLevel.objects.get_or_create(
            product=work_order.bom.product,
            warehouse=work_order.bom.warehouse,
            defaults={'quantity': 0}
        )
        sl.quantity += qty
        sl.save()

        work_order.status = 'completed'
        work_order.save()
