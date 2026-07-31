from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_user
from app.crud import create_product, get_products_with_stats, search_products
from app.schemas import ProductCreate, ProductResponse, ProductFilter

router = APIRouter(prefix="/products")

@router.post("", response_model=ProductResponse)
def create_product_endpoint(
    product: ProductCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_product(db, product, owner_id=current_user.id)

@router.get("", response_model=List[ProductResponse])
def list_products(
    filter: ProductFilter = Depends(),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = get_products_with_stats(db, current_user.id, filter)
    return products

@router.get("/search", response_model=List[ProductResponse])
def search_products_endpoint(
    query: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Поиск продуктов по подстроке в названии.
    Пример: GET /products/search?query=чай
    """
    if not query or not query.strip():
        return []

    products = search_products(db, owner_id=current_user.id, query=query.strip())
    return products