from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from ..database import get_db
from ..models import Item, Movement, RecipeLine
from ..schemas import ItemIn
from ..services import (cost_breakdown, creates_cycle, from_stock_units, get_setting, ifood_price,
                        item_units, markup_percent, to_stock_units, unit_cost)

router = APIRouter()


def display_line(line: RecipeLine) -> dict:
    """Quantidade na unidade em que foi digitada (1500 g), se ainda for compatível."""
    comp_unit = line.component.unit
    unit = line.unit or comp_unit
    try:
        qty = from_stock_units(line.quantity, unit, line.component)
    except ValueError:
        unit, qty = comp_unit, line.quantity
    return {"display_quantity": round(qty, 6), "display_unit": unit}


def display_yield(item: Item) -> dict:
    """Rendimento na unidade em que foi digitado (ex.: 3 kg pronto em vez de 10 porções)."""
    unit, qty = item.yield_unit or item.unit, item.yield_quantity
    if qty is not None and unit != item.unit:
        try:
            qty = from_stock_units(qty, unit, item)
        except ValueError:
            unit, qty = item.unit, item.yield_quantity
    return {"yield_display": None if qty is None else round(qty, 6), "yield_unit": unit}


def serialize(item: Item, memo=None, fee=None) -> dict:
    cost, issues = unit_cost(item, {} if memo is None else memo)
    if fee is None and item.kind == "venda":
        fee = get_setting(object_session(item), "ifood_fee_percent")
    data = {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "unit": item.unit,
        "stock": item.stock,
        "min_stock": item.min_stock,
        "coverage_days": item.coverage_days,
        "avg_cost": item.avg_cost,
        "yield_quantity": item.yield_quantity,
        **display_yield(item),
        "portion_size": item.portion_size,
        "portion_unit": item.portion_unit,
        "units": item_units(item),
        "min_batch": item.min_batch,
        "loss_percent": item.loss_percent or 0.0,
        "pack_size": item.pack_size,
        "pack_label": item.pack_label,
        "selling_price": item.selling_price,
        "notes": item.notes,
        "active": item.active,
        "recipe": [
            {
                "component_id": l.component_id,
                "component_name": l.component.name,
                "component_unit": l.component.unit,
                "quantity": l.quantity,
                "cost_quantity": round(l.cost_quantity, 6),
                "loss_percent": l.loss_percent,
                "effective_loss": l.effective_loss,
                **display_line(l),
            }
            for l in item.recipe
        ],
        "unit_cost": None if cost is None else round(cost, 6),
        "cost_issues": issues,
        "cmv_percent": None,
        "markup_percent": None,
        "ifood_price": None,
    }
    if item.kind == "venda":
        if cost and item.selling_price:
            data["cmv_percent"] = round(cost / item.selling_price * 100, 1)
        data["markup_percent"] = markup_percent(item.selling_price, cost)
        data["ifood_price"] = ifood_price(item.selling_price, fee)
    return data


def _get(db: Session, id: int) -> Item:
    item = db.get(Item, id)
    if not item:
        raise HTTPException(404, "Item não encontrado")
    return item


def _apply(db: Session, item: Item, data: ItemIn):
    if data.kind == "compra" and data.recipe:
        raise HTTPException(400, "Insumo comprado não tem ficha técnica")
    if item.id and data.kind == "venda":
        used = db.query(RecipeLine).filter_by(component_id=item.id).count()
        if used:
            raise HTTPException(400, "Este item é componente de outras fichas e não pode virar prato")

    ids = [l.component_id for l in data.recipe]
    if len(ids) != len(set(ids)):
        raise HTTPException(400, "Componente repetido na ficha técnica")
    quantities = []
    for line in data.recipe:
        comp = db.get(Item, line.component_id)
        if not comp:
            raise HTTPException(400, f"Componente {line.component_id} não existe")
        if comp.kind == "venda":
            raise HTTPException(400, f"'{comp.name}' é um prato e não pode ser componente")
        if item.id and (comp.id == item.id or creates_cycle(db, item.id, comp.id)):
            raise HTTPException(400, f"'{comp.name}' já usa este item: a ficha ficaria circular")
        try:
            quantities.append(to_stock_units(line.quantity, line.unit, comp))
        except ValueError:
            raise HTTPException(400, f"'{comp.name}' é controlado em {comp.unit}: use uma unidade compatível")

    item.name = data.name.strip()
    item.kind = data.kind
    item.unit = "un" if data.kind == "venda" else data.unit
    item.min_stock = data.min_stock
    item.loss_percent = data.loss_percent if data.kind != "venda" else 0.0
    item.coverage_days = data.coverage_days
    # porção com peso (só itens produzidos contados em "un")
    if data.kind == "producao" and item.unit == "un" and data.portion_size and data.portion_unit in ("g", "kg", "mL", "L"):
        item.portion_size, item.portion_unit = data.portion_size, data.portion_unit
    else:
        item.portion_size = item.portion_unit = None
    # rendimento pode vir em porções ou em peso (kg/g); grava na unidade de estoque
    item.yield_quantity, item.yield_unit = None, None
    if data.kind == "producao" and data.yield_quantity:
        try:
            item.yield_quantity = to_stock_units(data.yield_quantity, data.yield_unit, item)
        except ValueError:
            raise HTTPException(400, "Para informar o rendimento em peso, preencha o peso de cada porção")
        if data.yield_unit and data.yield_unit != item.unit:
            item.yield_unit = data.yield_unit
    item.min_batch = data.min_batch if data.kind == "producao" else 0.0
    item.pack_size = data.pack_size if data.kind == "compra" else None
    item.pack_label = data.pack_label if data.kind == "compra" else None
    item.selling_price = data.selling_price if data.kind == "venda" else None
    item.notes = data.notes
    item.active = data.active
    if data.avg_cost is not None:
        item.avg_cost = data.avg_cost
    item.recipe = [
        RecipeLine(component_id=l.component_id, quantity=q, unit=l.unit, loss_percent=l.loss_percent, position=i)
        for i, (l, q) in enumerate(zip(data.recipe, quantities))
    ]


def _commit(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Já existe um item com esse nome")


@router.get("")
def list_items(kind: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Item)
    if kind:
        q = q.filter(Item.kind == kind)
    memo, fee = {}, get_setting(db, "ifood_fee_percent")
    return [serialize(i, memo, fee) for i in q.order_by(Item.name).all()]


@router.post("", status_code=201)
def create_item(data: ItemIn, db: Session = Depends(get_db)):
    item = Item(stock=0.0, avg_cost=0.0)
    _apply(db, item, data)
    db.add(item)
    _commit(db)
    db.refresh(item)
    return serialize(item)


@router.get("/{id}")
def get_item(id: int, db: Session = Depends(get_db)):
    return serialize(_get(db, id))


@router.put("/{id}")
def update_item(id: int, data: ItemIn, db: Session = Depends(get_db)):
    item = _get(db, id)
    _apply(db, item, data)
    _commit(db)
    db.refresh(item)
    return serialize(item)


@router.delete("/{id}", status_code=204)
def delete_item(id: int, db: Session = Depends(get_db)):
    item = _get(db, id)
    parents = db.query(RecipeLine).filter_by(component_id=id).all()
    if parents:
        names = sorted({p.parent.name for p in parents})
        raise HTTPException(400, f"Usado nas fichas de: {', '.join(names)}")
    if db.query(Movement).filter_by(item_id=id).count():
        raise HTTPException(400, "Item tem histórico de estoque. Desative-o em vez de excluir.")
    db.delete(item)
    db.commit()


@router.get("/{id}/cost")
def item_cost(id: int, db: Session = Depends(get_db)):
    return cost_breakdown(_get(db, id))
