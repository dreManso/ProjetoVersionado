from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Item, Movement
from ..schemas import AdjustIn, PurchaseIn
from ..services import add_movement, convert_unit, current_cost, to_datetime, update_avg_cost

router = APIRouter()


def _stock_item(db: Session, id: int) -> Item:
    item = db.get(Item, id)
    if not item:
        raise HTTPException(404, "Item não encontrado")
    if item.kind == "venda":
        raise HTTPException(400, "Pratos não têm estoque; use os itens da ficha")
    return item


@router.post("/purchase")
def purchase(data: PurchaseIn, db: Session = Depends(get_db)):
    """Entrada de compra com peso/quantidade bruta e valor total pago."""
    item = _stock_item(db, data.item_id)
    try:
        quantity = convert_unit(data.quantity, data.unit, item.unit)
    except ValueError:
        raise HTTPException(400, f"'{item.name}' é controlado em {item.unit}: use uma unidade compatível")
    unit_price = data.total_price / quantity
    update_avg_cost(item, quantity, data.total_price)
    add_movement(db, item, quantity, "compra", unit_cost=unit_price,
                 when=to_datetime(data.day), notes=data.notes)
    db.commit()
    return {"item_id": item.id, "stock": item.stock, "avg_cost": round(item.avg_cost, 4),
            "unit_price": round(unit_price, 4)}


@router.post("/adjust")
def adjust(data: AdjustIn, db: Session = Depends(get_db)):
    """Contagem física: acerta o estoque e registra a diferença."""
    item = _stock_item(db, data.item_id)
    diff = data.counted_quantity - item.stock
    if abs(diff) > 1e-9:
        add_movement(db, item, diff, "ajuste", unit_cost=current_cost(item),
                     notes=data.notes or "Contagem de estoque")
        db.commit()
    return {"item_id": item.id, "stock": item.stock, "difference": round(diff, 4),
            "difference_value": round(diff * current_cost(item), 2)}


@router.get("/movements")
def movements(item_id: Optional[int] = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Movement)
    if item_id:
        q = q.filter(Movement.item_id == item_id)
    rows = q.order_by(Movement.date.desc(), Movement.id.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": m.id,
            "item_id": m.item_id,
            "item_name": m.item.name,
            "unit": m.item.unit,
            "type": m.type,
            "quantity": m.quantity,
            "unit_cost": m.unit_cost,
            "date": m.date,
            "notes": m.notes,
        }
        for m in rows
    ]
