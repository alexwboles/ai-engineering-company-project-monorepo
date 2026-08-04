from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=64)


class ProductSummary(BaseModel):
    id: int
    name: str
    sku: str


class ProductResponse(ProductSummary):
    current_stock: int


class InboundOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OutboundOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class InboundOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    created_at: datetime
    user_uuid: str
    order_type: Literal["inbound"]
    product: ProductSummary


class OutboundOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    created_at: datetime
    user_uuid: str
    order_type: Literal["outbound"]
    product: ProductSummary
