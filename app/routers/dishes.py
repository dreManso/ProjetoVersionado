from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Dish, DishComponent
from ..schemas import (
    DishCreate, DishRead, DishUpdate,
    DishCostResponse, ComponentCostDetail, DishComponentRead,
)
from ..services import calculate_dish_cost

router = APIRouter()


def _build_read(dish: Dish, db: Session) -> DishRead:
    try:
        cost = calculate_dish_cost(dish.id, db)
        total_cost = cost["total_cost"]
        cost_per_yield = cost["cost_per_yield_unit"]
        is_complete = cost["is_complete"]
    except Exception:
        total_cost = None
        cost_per_yield = None
        is_complete = False

    margin = None
    if dish.selling_price and total_cost:
        margin = round((dish.selling_price - total_cost) / dish.selling_price * 100, 2)

    components = [
        DishComponentRead(
            id=c.id,
            ingredient_id=c.ingredient_id,
            sub_dish_id=c.sub_dish_id,
            quantity=c.quantity,
            unit=c.unit,
            ingredient_name=c.ingredient.name if c.ingredient else None,
            sub_dish_name=c.sub_dish.name if c.sub_dish else None,
        )
        for c in dish.components
    ]

    return DishRead(
        id=dish.id,
        name=dish.name,
        description=dish.description,
        preparation_steps=dish.preparation_steps,
        yield_quantity=dish.yield_quantity,
        yield_unit=dish.yield_unit,
        selling_price=dish.selling_price,
        is_sellable=dish.is_sellable,
        created_at=dish.created_at,
        components=components,
        total_cost=total_cost,
        cost_per_yield_unit=cost_per_yield,
        is_cost_complete=is_complete,
        margin_percent=margin,
    )


def _apply_components(dish: Dish, components_data: list, db: Session):
    for c in dish.components:
        db.delete(c)
    db.flush()
    for comp in components_data:
        # prevent self-reference
        if comp.sub_dish_id == dish.id:
            raise HTTPException(400, "Uma preparação não pode usar a si mesma como componente")
        db.add(DishComponent(
            dish_id=dish.id,
            ingredient_id=comp.ingredient_id,
            sub_dish_id=comp.sub_dish_id,
            quantity=comp.quantity,
            unit=comp.unit,
        ))


@router.get("/", response_model=List[DishRead])
def list_dishes(db: Session = Depends(get_db)):
    dishes = db.query(Dish).order_by(Dish.name).all()
    return [_build_read(d, db) for d in dishes]


@router.post("/", response_model=DishRead, status_code=201)
def create_dish(data: DishCreate, db: Session = Depends(get_db)):
    dish = Dish(
        name=data.name,
        description=data.description,
        preparation_steps=data.preparation_steps,
        yield_quantity=data.yield_quantity,
        yield_unit=data.yield_unit,
        selling_price=data.selling_price,
        is_sellable=data.is_sellable,
    )
    db.add(dish)
    db.flush()
    _apply_components(dish, data.components, db)
    db.commit()
    db.refresh(dish)
    return _build_read(dish, db)


@router.get("/{id}", response_model=DishRead)
def get_dish(id: int, db: Session = Depends(get_db)):
    dish = db.get(Dish, id)
    if not dish:
        raise HTTPException(404, "Preparação não encontrada")
    return _build_read(dish, db)


@router.put("/{id}", response_model=DishRead)
def update_dish(id: int, data: DishUpdate, db: Session = Depends(get_db)):
    dish = db.get(Dish, id)
    if not dish:
        raise HTTPException(404, "Preparação não encontrada")

    update_data = data.model_dump(exclude_none=True)
    components_data = update_data.pop("components", None)

    for field, value in update_data.items():
        setattr(dish, field, value)

    if components_data is not None:
        _apply_components(dish, data.components, db)

    db.commit()
    db.refresh(dish)
    return _build_read(dish, db)


@router.delete("/{id}", status_code=204)
def delete_dish(id: int, db: Session = Depends(get_db)):
    dish = db.get(Dish, id)
    if not dish:
        raise HTTPException(404, "Preparação não encontrada")
    if dish.used_as_component:
        names = list({c.dish.name for c in dish.used_as_component})
        raise HTTPException(
            400,
            f"Esta preparação é usada como subproduto em: {', '.join(names)}. Remova-a das receitas antes de deletar."
        )
    db.delete(dish)
    db.commit()


@router.get("/{id}/cost", response_model=DishCostResponse)
def get_dish_cost(id: int, db: Session = Depends(get_db)):
    dish = db.get(Dish, id)
    if not dish:
        raise HTTPException(404, "Preparação não encontrada")

    cost = calculate_dish_cost(dish.id, db)

    margin = None
    if dish.selling_price and cost["total_cost"]:
        margin = round((dish.selling_price - cost["total_cost"]) / dish.selling_price * 100, 2)

    suggested = {}
    for pct in [30, 40, 50, 60]:
        if cost["total_cost"]:
            suggested[f"{pct}%"] = round(cost["total_cost"] / (1 - pct / 100), 2)

    return DishCostResponse(
        dish_id=dish.id,
        dish_name=dish.name,
        total_cost=cost["total_cost"],
        cost_per_yield_unit=cost["cost_per_yield_unit"],
        yield_quantity=dish.yield_quantity,
        yield_unit=dish.yield_unit,
        selling_price=dish.selling_price,
        margin_percent=margin,
        is_complete=cost["is_complete"],
        components=[ComponentCostDetail(**c) for c in cost["components"]],
        suggested_prices=suggested,
    )
