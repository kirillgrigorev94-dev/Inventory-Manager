from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.crud import add_batch
from app.schemas import BatchCreate, BatchResponse

router = APIRouter(prefix="/products/{product_id}/batches")

@router.post("", response_model=BatchResponse)
def add_batch_endpoint(
    product_id: int,
    batch: BatchCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    idempotency_key = None  # в реальном коде берём из заголовка Idempotency-Key
    created = add_batch(db, product_id, batch, owner_id=current_user.id, idempotency_key=idempotency_key)
    return created