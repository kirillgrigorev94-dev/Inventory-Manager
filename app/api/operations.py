from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.crud import consume_product
from app.schemas import ConsumeRequest
from app import models
import app.models as m

router = APIRouter(prefix="/products/{product_id}")

@router.post("/consume")
def consume_endpoint(
    product_id: int,
    data: ConsumeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # idempotency_key можно брать из заголовка
    consume_product(db, product_id, data, owner_id=current_user.id, idempotency_key=None)
    # Возвращаем актуальный остаток продукта
    product = db.query(models.Product).get(product_id)  # импортируй models
    return {"current_stock": product.current_stock}

@router.post("/batches/{batch_id}/discard")
def discard_batch(
    batch_id: int,
    payload: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quantity = payload.get("quantity")
    reason = payload.get("reason", "other")

    if quantity is None or quantity <= 0:
        raise HTTPException(400, "quantity must be > 0")

    batch = db.query(m.Batch).filter(
        m.Batch.id == batch_id,
        m.Batch.product.has(owner_id=current_user.id)
    ).first()

    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch.quantity_remaining < quantity:
        raise HTTPException(400, "Not enough remaining quantity in batch")

    batch.quantity_remaining -= quantity
    if batch.quantity_remaining <= 0:
        batch.status = m.BatchStatus.discarded

    op = m.Operation(
        product_id=batch.product_id,
        batch_id=batch.id,
        operation_type=m.OperationType.discard,
        quantity=quantity,
        comment=f"Discard reason: {reason}",
    )
    db.add(batch)
    db.add(op)
    db.commit()

    return {"status": "ok", "remaining": batch.quantity_remaining}


@router.post("/adjust")
def adjust_stock(
    product_id: int,
    payload: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    actual_quantity = payload.get("actual_quantity")
    comment = payload.get("comment", "Adjustment")

    if actual_quantity is None:
        raise HTTPException(400, "actual_quantity is required")

    product = db.query(m.Product).filter(
        m.Product.id == product_id,
        m.Product.owner_id == current_user.id
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")

    current = sum(
        b.quantity_remaining for b in product.batches
        if b.status not in [m.BatchStatus.consumed, m.BatchStatus.discarded]
    )

    diff = actual_quantity - current

    op = m.Operation(
        product_id=product.id,
        operation_type=m.OperationType.correction,
        quantity=diff,
        comment=comment,
    )
    db.add(op)
    db.commit()

    return {
        "current": current,
        "actual": actual_quantity,
        "difference": diff,
    }