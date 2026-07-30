from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.forecast import calculate_forecast

router = APIRouter(prefix="/products/{product_id}/forecast")

@router.get("")
def get_forecast(
    product_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    forecast = calculate_forecast(db, product_id)
    return forecast