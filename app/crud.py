from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from app import models, schemas
from app.models import Unit, BatchStatus, OperationType
from app.config import settings
import uuid
from fastapi import HTTPException
from .auth import get_password_hash

def get_products_with_stats(db: Session, user_id: int, filter_obj):
    q = db.query(models.Product).filter(models.Product.owner_id == user_id)

    if filter_obj.category:
        q = q.filter(models.Product.category == filter_obj.category)
    if filter_obj.search:
        q = q.filter(models.Product.name.ilike(f"%{filter_obj.search}%"))

    products = q.all()
    result = []
    for p in products:
        batches = [b for b in p.batches if b.status not in [models.BatchStatus.consumed, models.BatchStatus.discarded]]
        current_stock = sum(b.quantity_remaining for b in batches)
        min_exp = min((b.expires_at for b in batches if b.expires_at), default=None)
        count_batches = len(batches)

        status = "enough"
        if current_stock == 0:
            status = "out_of_stock"
        elif current_stock < p.minimum_stock:
            status = "low"
        elif min_exp and (min_exp - datetime.now()).days <= 3:
            status = "expiring_soon"
        elif min_exp and datetime.now() > min_exp:
            status = "expired"

        result.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "default_unit": p.default_unit,
            "minimum_stock": p.minimum_stock,
            "current_stock": current_stock,
            # доп. поля можно добавить по необходимости
        })
    return result

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)  # импортируй из auth.py
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_product(db: Session, product: schemas.ProductCreate, owner_id: int):
    db_product = models.Product(
        owner_id=owner_id,
        name=product.name,
        category=product.category,
        default_unit=product.default_unit.value,
        minimum_stock=product.minimum_stock,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def add_batch(
    db: Session,
    product_id: int,
    batch: schemas.BatchCreate,
    owner_id: int,
    idempotency_key: Optional[str] = None
):
    # Проверка прав: продукт должен принадлежать пользователю
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.owner_id == owner_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Идемпотентность: если ключ есть, проверяем, не создавали ли уже такую партию
    if idempotency_key:
        existing = db.query(models.Operation).filter(
            models.Operation.idempotency_key == idempotency_key,
            models.Operation.operation_type == OperationType.purchase
        ).first()
        if existing:
            # Возвращаем уже созданную партию через операцию
            batch_from_op = db.query(models.Batch).filter(models.Batch.id == existing.batch_id).first()
            return batch_from_op

    if batch.expires_at and batch.expires_at < batch.purchased_at:
        raise ValueError("expires_at cannot be earlier than purchased_at")

    db_batch = models.Batch(
        product_id=product_id,
        quantity_initial=batch.quantity,
        quantity_remaining=batch.quantity,
        purchased_at=datetime.combine(batch.purchased_at, datetime.min.time()),
        expires_at=datetime.combine(batch.expires_at, datetime.min.time()) if batch.expires_at else None,
        storage_location=batch.storage_location,
        price=batch.price,
    )
    db.add(db_batch)
    db.flush()  # чтобы получить id партии до коммита

    # Создаем операцию purchase
    op_key = idempotency_key or str(uuid.uuid4())
    db_operation = models.Operation(
        product_id=product_id,
        batch_id=db_batch.id,
        operation_type=OperationType.purchase,
        quantity=batch.quantity,
        idempotency_key=op_key,
    )
    db.add(db_operation)

    db.commit()
    db.refresh(db_batch)
    return db_batch

def consume_product(
    db: Session,
    product_id: int,
    data: schemas.ConsumeRequest,
    owner_id: int,
    idempotency_key: Optional[str] = None
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.owner_id == owner_id
    ).first()
    if not product:
        raise HTTPException(404, "Product not found")

    # Идемпотентность
    if idempotency_key:
        existing_op = db.query(models.Operation).filter(
            models.Operation.idempotency_key == idempotency_key,
            models.Operation.operation_type == models.OperationType.consume
        ).first()
        if existing_op:
            # Возвращаем текущий остаток продукта
            return product

    total_to_consume = data.quantity
    remaining = total_to_consume
    batches_to_update = []

    # Получаем активные партии
    active_batches = db.query(models.Batch).filter(
        models.Batch.product_id == product_id,
        models.Batch.status.notin_([BatchStatus.consumed, BatchStatus.discarded])
    ).all()

    if data.strategy == "manual":
        if not data.batch_id:
            raise ValueError("batch_id required for manual strategy")
        batch = next((b for b in active_batches if b.id == data.batch_id), None)
        if not batch:
            raise HTTPException(404, "Batch not found")
        active_batches = [batch]

    elif data.strategy == "expires_first":
        # Сортируем по ближайшему сроку годности (сначала те, что истекают раньше)
        active_batches.sort(key=lambda b: b.expires_at or datetime.max)

    elif data.strategy == "oldest_first":
        active_batches.sort(key=lambda b: b.purchased_at)

    else:
        raise ValueError("Invalid strategy")

    ops = []  # список операций для каждой затронутой партии

    for batch in active_batches:
        if remaining <= 0:
            break
        take = min(batch.quantity_remaining, remaining)
        if take <= 0:
            continue

        batch.quantity_remaining -= take
        remaining -= take

        # Обновляем статус партии
        if batch.quantity_remaining <= 0:
            batch.status = BatchStatus.consumed

        batches_to_update.append(batch)

        ops.append(models.Operation(
            product_id=product_id,
            batch_id=batch.id,
            operation_type=models.OperationType.consume,
            quantity=take,
            comment=data.comment,
            idempotency_key=idempotency_key
        ))

    if remaining > 0.0001:  # допуск на float
        raise HTTPException(400, "INSUFFICIENT_STOCK", details={"requested": total_to_consume, "available": total_to_consume - remaining})

    # Сохраняем изменения
    for b in batches_to_update:
        db.add(b)
    for op in ops:
        db.add(op)

    db.commit()
    return product