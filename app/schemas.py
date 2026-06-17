from pydantic import BaseModel, model_validator
from typing import Optional, List, Any
from datetime import datetime


# ── INGREDIENT ────────────────────────────────────────────────────────────────

class IngredientCreate(BaseModel):
    name: str
    unit: str
    cost_per_unit: float
    stock_quantity: float = 0.0
    min_stock: float = 0.0


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    cost_per_unit: Optional[float] = None
    min_stock: Optional[float] = None


class IngredientRead(BaseModel):
    id: int
    name: str
    unit: str
    cost_per_unit: float
    stock_quantity: float
    min_stock: float
    is_low_stock: bool = False

    model_config = {"from_attributes": True}


# ── DISH COMPONENT ─────────────────────────────────────────────────────────────

class DishComponentCreate(BaseModel):
    ingredient_id: Optional[int] = None
    sub_dish_id: Optional[int] = None
    quantity: float
    unit: str

    @model_validator(mode="after")
    def check_exactly_one_source(self):
        has_ing = self.ingredient_id is not None
        has_sub = self.sub_dish_id is not None
        if has_ing == has_sub:
            raise ValueError("Defina exatamente ingredient_id OU sub_dish_id")
        return self


class DishComponentRead(BaseModel):
    id: int
    ingredient_id: Optional[int]
    sub_dish_id: Optional[int]
    quantity: float
    unit: str
    ingredient_name: Optional[str] = None
    sub_dish_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ── DISH ───────────────────────────────────────────────────────────────────────

class DishCreate(BaseModel):
    name: str
    description: Optional[str] = None
    preparation_steps: Optional[str] = None
    yield_quantity: Optional[float] = None
    yield_unit: Optional[str] = None
    selling_price: Optional[float] = None
    is_sellable: bool = True
    components: List[DishComponentCreate] = []


class DishUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    preparation_steps: Optional[str] = None
    yield_quantity: Optional[float] = None
    yield_unit: Optional[str] = None
    selling_price: Optional[float] = None
    is_sellable: Optional[bool] = None
    components: Optional[List[DishComponentCreate]] = None


class DishRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    preparation_steps: Optional[str]
    yield_quantity: Optional[float]
    yield_unit: Optional[str]
    selling_price: Optional[float]
    is_sellable: bool
    created_at: datetime
    components: List[DishComponentRead] = []
    total_cost: Optional[float] = None
    cost_per_yield_unit: Optional[float] = None
    is_cost_complete: bool = False
    margin_percent: Optional[float] = None

    model_config = {"from_attributes": True}


# ── COST BREAKDOWN ─────────────────────────────────────────────────────────────

class ComponentCostDetail(BaseModel):
    type: str  # "ingredient" | "sub_dish"
    name: str
    quantity: float
    unit: str
    cost_per_unit: Optional[float] = None
    total: float
    is_complete: bool = True
    error: Optional[str] = None


class DishCostResponse(BaseModel):
    dish_id: int
    dish_name: str
    total_cost: float
    cost_per_yield_unit: Optional[float]
    yield_quantity: Optional[float]
    yield_unit: Optional[str]
    selling_price: Optional[float]
    margin_percent: Optional[float]
    is_complete: bool
    components: List[ComponentCostDetail]
    suggested_prices: dict


# ── SALE ───────────────────────────────────────────────────────────────────────

class SaleCreate(BaseModel):
    dish_id: int
    quantity_sold: float
    unit_price: float


class SaleRead(BaseModel):
    id: int
    dish_id: int
    dish_name: str
    quantity_sold: float
    unit_price: float
    total: float
    date: datetime

    model_config = {"from_attributes": True}


# ── STOCK ──────────────────────────────────────────────────────────────────────

class StockEntryCreate(BaseModel):
    ingredient_id: int
    quantity: float
    notes: Optional[str] = None


class StockMovementRead(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    movement_type: str
    quantity: float
    date: datetime
    notes: Optional[str]

    model_config = {"from_attributes": True}
