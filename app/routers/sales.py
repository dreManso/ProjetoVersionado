from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Sale, StockMovement, Ingredient, Dish
from ..schemas import SaleCreate, SaleRead
from ..services import get_raw_ingredients_needed

router = APIRouter()


@router.get("/", response_model=List[SaleRead])
def list_sales(db: Session = Depends(get_db)):
    sales = db.query(Sale).order_by(Sale.date.desc()).limit(100).all()
    return [
        SaleRead(
            id=s.id,
            dish_id=s.dish_id,
            dish_name=s.dish.name,
            quantity_sold=s.quantity_sold,
            unit_price=s.unit_price,
            total=s.total,
            date=s.date,
        )
        for s in sales
    ]


@router.post("/", response_model=SaleRead, status_code=201)
def register_sale(data: SaleCreate, db: Session = Depends(get_db)):
    dish = db.get(Dish, data.dish_id)
    if not dish:
        raise HTTPException(404, "Preparação não encontrada")
    if not dish.is_sellable:
        raise HTTPException(400, "Esta preparação não é marcada como vendável")

    try:
        raw_needs = get_raw_ingredients_needed(dish, data.quantity_sold, db)
    except ValueError as e:
        raise HTTPException(400, str(e))

    sale = Sale(
        dish_id=data.dish_id,
        quantity_sold=data.quantity_sold,
        unit_price=data.unit_price,
        total=round(data.quantity_sold * data.unit_price, 2),
    )
    db.add(sale)
    db.flush()

    for ing_id, qty_needed in raw_needs.items():
        ing = db.get(Ingredient, ing_id)
        if ing:
            ing.stock_quantity = max(0.0, ing.stock_quantity - qty_needed)
            db.add(StockMovement(
                ingredient_id=ing_id,
                movement_type="out",
                quantity=round(qty_needed, 4),
                sale_id=sale.id,
                notes=f"Venda: {dish.name} × {data.quantity_sold}",
            ))

    db.commit()
    db.refresh(sale)

    return SaleRead(
        id=sale.id,
        dish_id=sale.dish_id,
        dish_name=dish.name,
        quantity_sold=sale.quantity_sold,
        unit_price=sale.unit_price,
        total=sale.total,
        date=sale.date,
    )
