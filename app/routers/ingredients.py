from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Ingredient, StockMovement
from ..schemas import IngredientCreate, IngredientRead, IngredientUpdate, StockEntryCreate, StockMovementRead

router = APIRouter()


def _to_read(ing: Ingredient) -> IngredientRead:
    data = IngredientRead.model_validate(ing)
    data.is_low_stock = ing.stock_quantity < ing.min_stock
    return data


@router.get("/", response_model=List[IngredientRead])
def list_ingredients(db: Session = Depends(get_db)):
    return [_to_read(i) for i in db.query(Ingredient).order_by(Ingredient.name).all()]


@router.post("/", response_model=IngredientRead, status_code=201)
def create_ingredient(data: IngredientCreate, db: Session = Depends(get_db)):
    ing = Ingredient(**data.model_dump())
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return _to_read(ing)


@router.get("/{id}", response_model=IngredientRead)
def get_ingredient(id: int, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, id)
    if not ing:
        raise HTTPException(404, "Ingrediente não encontrado")
    return _to_read(ing)


@router.put("/{id}", response_model=IngredientRead)
def update_ingredient(id: int, data: IngredientUpdate, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, id)
    if not ing:
        raise HTTPException(404, "Ingrediente não encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(ing, field, value)
    db.commit()
    db.refresh(ing)
    return _to_read(ing)


@router.delete("/{id}", status_code=204)
def delete_ingredient(id: int, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, id)
    if not ing:
        raise HTTPException(404, "Ingrediente não encontrado")
    if ing.components:
        raise HTTPException(400, "Ingrediente em uso em uma ou mais preparações — remova-o das receitas primeiro")
    db.delete(ing)
    db.commit()


@router.post("/{id}/stock")
def add_stock(id: int, data: StockEntryCreate, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, id)
    if not ing:
        raise HTTPException(404, "Ingrediente não encontrado")
    ing.stock_quantity += data.quantity
    movement = StockMovement(
        ingredient_id=id,
        movement_type="in",
        quantity=data.quantity,
        notes=data.notes,
    )
    db.add(movement)
    db.commit()
    db.refresh(ing)
    return _to_read(ing)


@router.get("/{id}/movements", response_model=List[StockMovementRead])
def get_movements(id: int, db: Session = Depends(get_db)):
    ing = db.get(Ingredient, id)
    if not ing:
        raise HTTPException(404, "Ingrediente não encontrado")
    movements = (
        db.query(StockMovement)
        .filter(StockMovement.ingredient_id == id)
        .order_by(StockMovement.date.desc())
        .limit(50)
        .all()
    )
    return [
        StockMovementRead(
            id=m.id,
            ingredient_id=m.ingredient_id,
            ingredient_name=ing.name,
            movement_type=m.movement_type,
            quantity=m.quantity,
            date=m.date,
            notes=m.notes,
        )
        for m in movements
    ]
