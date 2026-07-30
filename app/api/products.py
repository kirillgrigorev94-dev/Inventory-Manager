from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.crud import create_product, get_products_with_stats
from app.schemas import ProductCreate, ProductResponse, ProductFilter

router = APIRouter(prefix="/products")

@router.post("", response_model=ProductResponse)
def create_product_endpoint(
    product: ProductCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_product(db, product, owner_id=current_user.id)

@router.get("", response_model=list[ProductResponse])
def list_products(
    filter: ProductFilter = Depends(),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = get_products_with_stats(db, current_user.id, filter)
    return products