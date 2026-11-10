from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Kind = Literal["compra", "producao", "venda"]
Unit = Literal["kg", "g", "L", "mL", "un"]


class RecipeLineIn(BaseModel):
    component_id: int
    quantity: float = Field(gt=0)
    unit: Optional[Unit] = None  # se diferente da unidade do componente, é convertida (g→kg...)
    loss_percent: Optional[float] = Field(None, ge=0, le=95)  # perda nesta receita; vazio = padrão do item


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Kind
    unit: Unit = "un"
    min_stock: float = Field(0.0, ge=0)
    coverage_days: float = Field(6.0, ge=0)
    avg_cost: Optional[float] = Field(None, ge=0)  # só aplicado se enviado
    yield_quantity: Optional[float] = Field(None, gt=0)
    yield_unit: Optional[Unit] = None          # unidade em que o rendimento foi digitado (ex.: kg pronto)
    portion_size: Optional[float] = Field(None, gt=0)   # peso/volume de cada porção (itens em "un")
    portion_unit: Optional[Unit] = None
    min_batch: float = Field(0.0, ge=0)
    loss_percent: float = Field(0.0, ge=0, le=95)  # perda no preparo (casca, descongelamento...)
    pack_size: Optional[float] = Field(None, gt=0)
    pack_label: Optional[str] = None
    selling_price: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    active: bool = True
    recipe: List[RecipeLineIn] = []


class PurchaseIn(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)        # peso/quantidade bruta total
    unit: Optional[Unit] = None          # unidade da quantidade (convertida para a do item)
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
    output_unit: Optional[Unit] = None   # ex.: rendeu 3 kg de uma porção de 300 g → 10 un
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
