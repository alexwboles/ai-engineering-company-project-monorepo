from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

try:
    from ..auth_models import UserRecord
    from ..auth_security import get_current_user
    from ..database import get_db
    from ..models import InboundOrder, OutboundOrder, Product
    from ..schemas import (
        InboundOrderCreate,
        InboundOrderResponse,
        OutboundOrderCreate,
        OutboundOrderResponse,
        ProductCreate,
        ProductResponse,
        ProductSummary,
    )
except (ImportError, ValueError):
    from auth_models import UserRecord
    from auth_security import get_current_user
    from database import get_db
    from models import InboundOrder, OutboundOrder, Product
    from schemas import (
        InboundOrderCreate,
        InboundOrderResponse,
        OutboundOrderCreate,
        OutboundOrderResponse,
        ProductCreate,
        ProductResponse,
        ProductSummary,
    )

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _stock_expression():
    inbound_total = (
        select(func.coalesce(func.sum(InboundOrder.quantity), 0))
        .where(InboundOrder.product_id == Product.id)
        .correlate(Product)
        .scalar_subquery()
    )
    outbound_total = (
        select(func.coalesce(func.sum(OutboundOrder.quantity), 0))
        .where(OutboundOrder.product_id == Product.id)
        .correlate(Product)
        .scalar_subquery()
    )
    return inbound_total - outbound_total


def _product_rows(session: Session, product_id: int | None = None) -> list[tuple[Product, int]]:
    statement = select(Product, _stock_expression().label("current_stock"))
    if product_id is not None:
        statement = statement.where(Product.id == product_id)
    return list(session.exec(statement).all())


def _product_response(product: Product, current_stock: int) -> ProductResponse:
    if product.id is None:
        raise HTTPException(status_code=500, detail="Product identifier was not generated.")
    return ProductResponse(
        id=product.id,
        name=product.name,
        sku=product.sku,
        current_stock=int(current_stock),
    )


def _product_summary(product: Product) -> ProductSummary:
    if product.id is None:
        raise HTTPException(status_code=500, detail="Product identifier was not generated.")
    return ProductSummary(id=product.id, name=product.name, sku=product.sku)


def _order_payload(order: Any, product: Product) -> dict[str, Any]:
    if order.id is None:
        raise HTTPException(status_code=500, detail="Order identifier was not generated.")
    return {
        "id": order.id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "created_at": order.created_at,
        "user_uuid": order.user_uuid,
        "product": _product_summary(product),
    }


def _get_product(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


def _current_stock(session: Session, product_id: int) -> int:
    rows = _product_rows(session, product_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found.")
    return int(rows[0][1])


@router.get("/products", response_model=list[ProductResponse])
def list_products(session: Session = Depends(get_db)) -> list[ProductResponse]:
    return [_product_response(product, stock) for product, stock in _product_rows(session)]


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> ProductResponse:
    _ = current_user
    product = Product(name=payload.name, sku=payload.sku)
    session.add(product)
    try:
        session.commit()
        session.refresh(product)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="A product with that SKU already exists.") from None
    return _product_response(product, 0)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, session: Session = Depends(get_db)) -> ProductResponse:
    rows = _product_rows(session, product_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found.")
    product, stock = rows[0]
    return _product_response(product, stock)


@router.post("/orders/inbound", response_model=InboundOrderResponse, status_code=status.HTTP_201_CREATED)
def create_inbound_order(
    payload: InboundOrderCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> InboundOrderResponse:
    product = _get_product(session, payload.product_id)
    order = InboundOrder(
        product_id=payload.product_id,
        quantity=payload.quantity,
        created_at=datetime.now(timezone.utc),
        user_uuid=str(current_user.id),
    )
    session.add(order)
    try:
        session.commit()
        session.refresh(order)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Unable to register the inbound order.") from None
    return InboundOrderResponse.model_validate(_order_payload(order, product))


@router.post("/orders/outbound", response_model=OutboundOrderResponse, status_code=status.HTTP_201_CREATED)
def create_outbound_order(
    payload: OutboundOrderCreate,
    session: Session = Depends(get_db),
    current_user: UserRecord = Depends(get_current_user),
) -> OutboundOrderResponse:
    product = _get_product(session, payload.product_id)
    available_stock = _current_stock(session, payload.product_id)
    if payload.quantity > available_stock:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock for product {payload.product_id}. Available stock: {available_stock}.",
        )

    order = OutboundOrder(
        product_id=payload.product_id,
        quantity=payload.quantity,
        created_at=datetime.now(timezone.utc),
        user_uuid=str(current_user.id),
    )
    session.add(order)
    try:
        session.commit()
        session.refresh(order)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Unable to register the outbound order.") from None
    return OutboundOrderResponse.model_validate(_order_payload(order, product))


@router.get("/orders", response_model=list[InboundOrderResponse | OutboundOrderResponse])
def list_orders(session: Session = Depends(get_db)) -> list[InboundOrderResponse | OutboundOrderResponse]:
    inbound_rows = session.exec(
        select(InboundOrder, Product).join(Product, Product.id == InboundOrder.product_id)
    ).all()
    outbound_rows = session.exec(
        select(OutboundOrder, Product).join(Product, Product.id == OutboundOrder.product_id)
    ).all()

    orders: list[InboundOrderResponse | OutboundOrderResponse] = [
        InboundOrderResponse.model_validate(_order_payload(order, product)) for order, product in inbound_rows
    ]
    orders.extend(
        OutboundOrderResponse.model_validate(_order_payload(order, product)) for order, product in outbound_rows
    )
    return sorted(orders, key=lambda order: order.created_at)
