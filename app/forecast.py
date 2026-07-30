from datetime import timedelta, datetime
from sqlalchemy.orm import Session
from app import models

def calculate_forecast(db: Session, product_id: int, days_lookback: int = 14):
    consume_ops = db.query(models.Operation).filter(
        models.Operation.product_id == product_id,
        models.Operation.operation_type == models.OperationType.consume
    ).order_by(models.Operation.created_at.desc()).limit(days_lookback).all()

    if len(consume_ops) < 2:
        return {
            "estimated_depletion_date": None,
            "confidence": "insufficient_data",
            "based_on_days": len(consume_ops),
        }

    total_consumed = sum(op.quantity for op in consume_ops)
    avg_daily = total_consumed / days_lookback

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    current_stock = product.current_stock if hasattr(product, "current_stock") else sum(
        b.quantity_remaining for b in product.batches
        if b.status not in [models.BatchStatus.consumed, models.BatchStatus.discarded]
    )

    if avg_daily <= 0:
        return {"estimated_depletion_date": None, "confidence": "low", "based_on_days": days_lookback}

    days_remaining = current_stock / avg_daily
    estimated_date = datetime.now() + timedelta(days=days_remaining)

    confidence = "medium"
    if days_lookback >= 28:
        confidence = "high"
    elif days_lookback < 7:
        confidence = "low"

    return {
        "product_id": product_id,
        "current_stock": current_stock,
        "average_daily_consumption": avg_daily,
        "estimated_days_remaining": days_remaining,
        "estimated_depletion_date": estimated_date.date(),
        "confidence": confidence,
        "based_on_days": days_lookback,
    }