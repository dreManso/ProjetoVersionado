from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ingredient, Dish, Sale, StockMovement
from ..services import calculate_dish_cost
from ..schemas import StockMovementRead

router = APIRouter()


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    total_dishes = db.query(Dish).count()
    total_ingredients = db.query(Ingredient).count()
    low_stock = db.query(Ingredient).filter(
        Ingredient.stock_quantity < Ingredient.min_stock
    ).count()
    today_sales = db.query(func.sum(Sale.total)).filter(
        func.date(Sale.date) == func.date("now")
    ).scalar() or 0.0
    total_sales = db.query(func.sum(Sale.total)).scalar() or 0.0
    total_sales_count = db.query(Sale).count()

    return {
        "total_dishes": total_dishes,
        "total_ingredients": total_ingredients,
        "low_stock_alerts": low_stock,
        "today_sales": round(today_sales, 2),
        "total_sales": round(total_sales, 2),
        "total_sales_count": total_sales_count,
    }


@router.get("/stock-alerts")
def stock_alerts(db: Session = Depends(get_db)):
    ingredients = db.query(Ingredient).filter(
        Ingredient.stock_quantity < Ingredient.min_stock
    ).all()
    return sorted(
        [
            {
                "id": i.id,
                "name": i.name,
                "unit": i.unit,
                "stock_quantity": i.stock_quantity,
                "min_stock": i.min_stock,
                "deficit": round(i.min_stock - i.stock_quantity, 4),
            }
            for i in ingredients
        ],
        key=lambda x: x["deficit"],
        reverse=True,
    )


@router.get("/dish-costs")
def dish_costs(db: Session = Depends(get_db)):
    dishes = db.query(Dish).order_by(Dish.name).all()
    result = []
    for dish in dishes:
        try:
            cost = calculate_dish_cost(dish.id, db)
            margin = None
            if dish.selling_price and cost["total_cost"]:
                margin = round(
                    (dish.selling_price - cost["total_cost"]) / dish.selling_price * 100, 2
                )
            result.append({
                "id": dish.id,
                "name": dish.name,
                "is_sellable": dish.is_sellable,
                "total_cost": cost["total_cost"],
                "cost_per_yield_unit": cost["cost_per_yield_unit"],
                "yield_quantity": dish.yield_quantity,
                "yield_unit": dish.yield_unit,
                "selling_price": dish.selling_price,
                "margin_percent": margin,
                "is_complete": cost["is_complete"],
            })
        except Exception as e:
            result.append({
                "id": dish.id,
                "name": dish.name,
                "is_sellable": dish.is_sellable,
                "total_cost": None,
                "cost_per_yield_unit": None,
                "yield_quantity": dish.yield_quantity,
                "yield_unit": dish.yield_unit,
                "selling_price": dish.selling_price,
                "margin_percent": None,
                "is_complete": False,
                "error": str(e),
            })
    return sorted(result, key=lambda x: x["total_cost"] or 0, reverse=True)


@router.get("/movements")
def all_movements(db: Session = Depends(get_db)):
    movements = (
        db.query(StockMovement)
        .order_by(StockMovement.date.desc())
        .limit(100)
        .all()
    )
    return [
        StockMovementRead(
            id=m.id,
            ingredient_id=m.ingredient_id,
            ingredient_name=m.ingredient.name,
            movement_type=m.movement_type,
            quantity=m.quantity,
            date=m.date,
            notes=m.notes,
        )
        for m in movements
    ]
