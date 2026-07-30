from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.database import Base

class Unit(PyEnum):
    piece = "piece"
    gram = "gram"
    kilogram = "kilogram"
    milliliter = "milliliter"
    liter = "liter"
    package = "package"

class OperationType(PyEnum):
    purchase = "purchase"
    consume = "consume"
    discard = "discard"
    correction = "correction"
    transfer = "transfer"

class BatchStatus(PyEnum):
    fresh = "fresh"
    expiring_soon = "expiring_soon"
    expired = "expired"
    consumed = "consumed"
    discarded = "discarded"

class NotificationType(PyEnum):
    expires_soon = "expires_soon"
    expired = "expired"
    low_stock = "low_stock"
    will_run_out = "will_run_out"
    waste_risk = "waste_risk"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")
    shopping_list_items = relationship("ShoppingListItem", back_populates="user")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, index=True)
    default_unit = Column(String, nullable=False)  # piece, gram, liter...
    minimum_stock = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="products")
    batches = relationship("Batch", back_populates="product", cascade="all, delete-orphan")
    operations = relationship("Operation", back_populates="product")
    recommendations = relationship("Recommendation", back_populates="product")

    @property
    def current_stock(self):
        return sum(b.quantity_remaining for b in self.batches if b.status != BatchStatus.discarded and b.status != BatchStatus.consumed)

class Batch(Base):
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity_initial = Column(Float, nullable=False)
    quantity_remaining = Column(Float, nullable=False)
    purchased_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    storage_location = Column(String)
    price = Column(Float, default=0.0)
    status = Column(Enum(BatchStatus), default=BatchStatus.fresh)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="batches")
    operations = relationship("Operation", back_populates="batch")

class Operation(Base):
    __tablename__ = "operations"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True, index=True)
    operation_type = Column(Enum(OperationType), nullable=False)
    quantity = Column(Float, nullable=False)
    comment = Column(String)
    idempotency_key = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="operations")
    batch = relationship("Batch")

class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    recommended_quantity = Column(Float)
    reason = Column(String)
    priority = Column(String, default="medium")
    added_automatically = Column(Boolean, default=False)
    is_purchased = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="shopping_list_items")
    product = relationship("Product")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(Enum(NotificationType), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True, index=True)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notifications")
    product = relationship("Product")
    batch = relationship("Batch")

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    rec_type = Column(String, nullable=False)  # use_soon, buy, check_stock, waste_risk
    priority = Column(String, default="medium")
    message = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    expected_unused_quantity = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="recommendations")