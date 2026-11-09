from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Kind = Literal["compra", "producao", "venda"]
Unit = Literal["kg", "g", "L", "mL", "un"]


class RecipeLineIn(BaseModel):
    component_id: int
    quantity: float = Field(gt=0)


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Kind
    unit: Unit = "un"
    min_stock: float = Field(0.0, ge=0)
    coverage_days: float = Field(6.0, ge=0)
    avg_cost: Optional[float] = Field(None, ge=0)  # só aplicado se enviado
    yield_quantity: Optional[float] = Field(None, gt=0)
    min_batch: float = Field(0.0, ge=0)
    pack_size: Optional[float] = Field(None, gt=0)
    pack_label: Optional[str] = None
    selling_price: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    active: bool = True
    recipe: List[RecipeLineIn] = []


class PurchaseIn(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)        # peso/quantidade bruta total
    total_price: float = Field(ge=0)     # valor total pago
    day: Optional[date] = None
    notes: Optional[str] = None


class AdjustIn(BaseModel):
    item_id: int
    counted_quantity: float = Field(ge=0)
    notes: Optional[str] = None


class ProductionInputIn(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)


class ProductionIn(BaseModel):
    item_id: int
    output_quantity: float = Field(gt=0)
    inputs: List[ProductionInputIn] = Field(min_length=1)
    day: Optional[date] = None
    notes: Optional[str] = None


class SaleLineIn(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)
    unit_price: Optional[float] = Field(None, ge=0)


class SalesIn(BaseModel):
    day: Optional[date] = None
    lines: List[SaleLineIn] = Field(min_length=1)
