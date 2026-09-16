from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.services import get_sequence_next, log_audit

ZERO = Decimal('0.00')


def next_number(company, prefix, padding=4):
    seq_name = f'{prefix}{company.pk}'
    return get_sequence_next(seq_name, prefix=prefix, padding=padding)


def on_hand(product, warehouse=None):
    qs = product.stocks.all()
    if warehouse:
        qs = qs.filter(warehouse=warehouse)
    return qs.aggregate(total=Sum('quantity'))['total'] or ZERO


def apply_stock_movement(company, *, product, warehouse, quantity, unit_cost,
                         movement_type, to_warehouse=None, date=None,
                         reference_type='', reference_id=None, reference_number='',
                         notes='', user=None):
    from apps.inventory.models import StockLevel, StockMovement

    if company is None:
        raise ValueError('A company is required to post a stock movement.')
    qty = Decimal(quantity)
    cost = Decimal(unit_cost)
    with transaction.atomic():
        level, _created = StockLevel.objects.select_for_update().get_or_create(
            company=company, product=product, warehouse=warehouse,
            defaults={'quantity': ZERO, 'avg_cost': product.avg_cost or ZERO},
        )
        prev_qty = level.quantity
        prev_cost = level.avg_cost
        new_qty = prev_qty + qty
        if qty > 0:
            total_value = (prev_qty * prev_cost) + (qty * cost)
            level.avg_cost = (total_value / new_qty) if new_qty else cost
        level.quantity = new_qty
        level.save()
        StockMovement.objects.create(
            company=company, product=product, warehouse=warehouse,
            to_warehouse=to_warehouse, quantity=qty, unit_cost=cost,
            date=date or timezone.now(), type=movement_type,
            reference_type=reference_type, reference_id=reference_id,
            reference_number=reference_number, notes=notes, created_by=user,
        )
    return level


def move_between(company, *, product, from_warehouse, to_warehouse, quantity,
                 movement_type, date=None, reference_type='', reference_id=None,
                 reference_number='', notes='', user=None):
    from apps.inventory.models import StockLevel

    qty = Decimal(quantity)
    src = StockLevel.objects.filter(company=company, product=product, warehouse=from_warehouse).first()
    src_qty = src.quantity if src else ZERO
    if src_qty < qty:
        raise ValueError(f'Insufficient stock of {product} in {from_warehouse}: {src_qty} available.')
    unit_cost = src.avg_cost if src else (product.avg_cost or ZERO)
    with transaction.atomic():
        apply_stock_movement(
            company, product=product, warehouse=from_warehouse, quantity=-qty,
            unit_cost=unit_cost, movement_type=movement_type, to_warehouse=to_warehouse,
            date=date, reference_type=reference_type, reference_id=reference_id,
            reference_number=reference_number, notes=notes, user=user,
        )
        apply_stock_movement(
            company, product=product, warehouse=to_warehouse, quantity=qty,
            unit_cost=unit_cost, movement_type=movement_type,
            date=date, reference_type=reference_type, reference_id=reference_id,
            reference_number=reference_number, notes=f'Inbound {notes}'.strip(), user=user,
        )


def post_transfer(transfer, user=None):
    from apps.inventory.models import StockTransfer

    if transfer.status == StockTransfer.Status.POSTED:
        return transfer
    if transfer.status == StockTransfer.Status.CANCELLED:
        raise ValueError('A cancelled transfer cannot be posted.')
    if transfer.from_warehouse_id == transfer.to_warehouse_id:
        raise ValueError('Source and destination warehouses must differ.')
    with transaction.atomic():
        for line in transfer.lines:
            move_between(
                transfer.company, product=line.product,
                from_warehouse=transfer.from_warehouse, to_warehouse=transfer.to_warehouse,
                quantity=line.quantity, movement_type='transfer',
                reference_type='STOCK_TRANSFER', reference_id=transfer.pk,
                reference_number=transfer.number, notes=transfer.notes, user=user,
            )
        transfer.status = StockTransfer.Status.POSTED
        transfer.posted_at = timezone.now()
        transfer.save()
    log_audit(user, 'post', 'StockTransfer', transfer.pk, f'Posted {transfer.number}')
    return transfer


def post_adjustment(adjustment, user=None):
    from apps.inventory.models import StockAdjustment, StockMovement

    if adjustment.status == StockAdjustment.Status.POSTED:
        return adjustment
    if adjustment.status == StockAdjustment.Status.CANCELLED:
        raise ValueError('A cancelled adjustment cannot be posted.')
    with transaction.atomic():
        for line in adjustment.lines.all():
            qty = Decimal(line.quantity)
            if qty < 0:
                available = adjustment.warehouse.stocks.filter(company=adjustment.company, product=line.product).aggregate(t=Sum('quantity'))['t'] or ZERO
                if available < -qty:
                    raise ValueError(f'Adjustment for {line.product} exceeds available stock ({available}).')
            unit_cost = line.product.avg_cost or ZERO
            apply_stock_movement(
                adjustment.company, product=line.product, warehouse=adjustment.warehouse,
                quantity=qty, unit_cost=unit_cost, movement_type=StockMovement.MovementType.ADJUSTMENT,
                reference_type='STOCK_ADJUSTMENT', reference_id=adjustment.pk,
                reference_number=adjustment.number, notes=line.reason or adjustment.reason,
                user=user,
            )
        adjustment.status = StockAdjustment.Status.POSTED
        adjustment.posted_at = timezone.now()
        adjustment.save()
    log_audit(user, 'post', 'StockAdjustment', adjustment.pk, f'Posted {adjustment.number}')
    return adjustment