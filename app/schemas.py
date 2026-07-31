from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

class Unit(str, Enum):
    piece = "piece"
    gram = "gram"
    kilogram = "kilogram"
    milliliter = "milliliter"
    liter = "liter"
    package = "package"

class OperationType(str, Enum):
    purchase = "purchase"
    consume = "consume"
    discard = "discard"
    correction = "correction"
    transfer = "transfer"

class BatchStatus(str, Enum):
    fresh = "fresh"
    expiring_soon = "expiring_soon"
    expired = "expired"
    consumed = "consumed"
    discarded = "discarded"

# Auth
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserMe(BaseModel):
    id: int
    username: str

# Products
class ProductCreate(BaseModel):
    name: str
    category: str
    default_unit: Unit
    minimum_stock: float = Field(ge=0)

class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    default_unit: str
    minimum_stock: float
    current_stock: float

class ProductFilter(BaseModel):
    category: Optional[str] = None
    storage_location: Optional[str] = None
    low_stock: Optional[bool] = None
    expiring_soon: Optional[bool] = None
    search: Optional[str] = None

# Batches
class BatchCreate(BaseModel):
    quantity: float = Field(gt=0)
    purchased_at: date
    expires_at: Optional[date] = None
    storage_location: str
    price: float = Field(ge=0)

class BatchResponse(BaseModel):
    id: int
    product_id: int
    quantity_initial: float
    quantity_remaining: float
    purchased_at: date
    expires_at: Optional[date] = None
    storage_location: str
    status: BatchStatus

# Consume
class ConsumeRequest(BaseModel):
    quantity: float = Field(gt=0)
    strategy: str = Field(default="expires_first", pattern="^(expires_first|oldest_first|manual)$")
    batch_id: Optional[int] = None
    comment: Optional[str] = None

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict

# Notifications
class NotificationResponse(BaseModel):
    id: int
    type: str
    product_id: Optional[int]
    batch_id: Optional[int]
    message: str
    created_at: datetime
    read_at: Optional[datetime]

# Analytics
class AnalyticsResponse(BaseModel):
    period: dict
    total_spent: float
    discarded_value: float
    waste_percent: float
    most_consumed_products: list