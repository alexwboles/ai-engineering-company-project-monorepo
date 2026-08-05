from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Field as SQLModelField
from sqlmodel import SQLModel

PRODUCT_CATEGORIES: tuple[str, ...] = (
    "medical_equipment",
    "pharmaceuticals",
    "diagnostic_supplies",
    "it_services",
    "facility_services",
)

SUPPLIER_STATUSES: tuple[str, ...] = ("active", "suspended")

INITIAL_SUPPLIERS: tuple[dict[str, object], ...] = (
    {
        "name": "Medline Distribution",
        "country": "US",
        "product_categories": ["medical_equipment", "diagnostic_supplies"],
        "rate": 4.4,
        "status": "active",
    },
    {
        "name": "BritPharm Logistics",
        "country": "UK",
        "product_categories": ["pharmaceuticals"],
        "rate": 4.1,
        "status": "active",
    },
    {
        "name": "SteriTech Solutions",
        "country": "US",
        "product_categories": ["facility_services", "it_services"],
        "rate": 3.9,
        "status": "suspended",
    },
)


class SupplierStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ProductCategory(str, Enum):
    MEDICAL_EQUIPMENT = "medical_equipment"
    PHARMACEUTICALS = "pharmaceuticals"
    DIAGNOSTIC_SUPPLIES = "diagnostic_supplies"
    IT_SERVICES = "it_services"
    FACILITY_SERVICES = "facility_services"


class SupplierCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    country: str = Field(min_length=2)
    product_categories: list[ProductCategory] = Field(min_length=1)
    rate: float
    status: SupplierStatus

    @field_validator("rate")
    @classmethod
    def validate_positive_rate(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("rate must be greater than zero")
        return value


class SupplierResponse(SupplierCreate):
    id: int
    last_rate_update_date: date
    updated_at: datetime


class SupplierRateUpdate(BaseModel):
    rate: float

    @field_validator("rate")
    @classmethod
    def validate_positive_rate(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("rate must be greater than zero")
        return value


class SupplierStatusUpdate(BaseModel):
    status: SupplierStatus


class Product(SQLModel, table=True):
    """Supabase product identity; stock is derived from order history."""

    __tablename__ = "products"

    id: int | None = SQLModelField(default=None, primary_key=True)
    name: str = SQLModelField(index=True, max_length=200)
    sku: str = SQLModelField(index=True, unique=True, max_length=64)


class InboundOrder(SQLModel, table=True):
    """Immutable order fact that adds quantity to a product's derived stock."""

    __tablename__ = "inbound_orders"

    id: int | None = SQLModelField(default=None, primary_key=True)
    product_id: int = SQLModelField(foreign_key="products.id", index=True)
    quantity: int = SQLModelField(gt=0)
    created_at: datetime = SQLModelField(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str = SQLModelField(index=True, max_length=64)


class OutboundOrder(SQLModel, table=True):
    """Immutable order fact that subtracts quantity from derived stock."""

    __tablename__ = "outbound_orders"

    id: int | None = SQLModelField(default=None, primary_key=True)
    product_id: int = SQLModelField(foreign_key="products.id", index=True)
    quantity: int = SQLModelField(gt=0)
    created_at: datetime = SQLModelField(default_factory=lambda: datetime.now(timezone.utc))
    user_uuid: str = SQLModelField(index=True, max_length=64)
