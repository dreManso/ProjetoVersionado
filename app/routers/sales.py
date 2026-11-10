from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Item, Movement, Sale
from ..schemas import SalesIn
from ..services import add_movement, current_cost, get_setting, ifood_price, to_datetime

router = APIRouter()


@router.post("", status_code=201)
def register_sales(data: SalesIn, db: Session = Depends(get_db)):
    """
    Fechamento do dia (ou venda avulsa): para cada prato vendido,
    baixa os componentes da ficha — as porções prontas e as embalagens.
    """
    when = to_datetime(data.day)
    created, total, warnings = 0, 0.0, []

    for line in data.lines:
        dish = db.get(Item, line.item_id)
        if not dish or dish.kind != "venda":
            raise HTTPException(400, f"Item {line.item_id} não é um prato do cardápio")
        if line.unit_price is not None:
            price = line.unit_price
        elif data.channel == "ifood":
            price = ifood_price(dish.selling_price, get_setting(db, "ifood_fee_percent")) or 0.0
        else:
            price = dish.selling_price or 0.0
        sale = Sale(item_id=dish.id, quantity=line.quantity, unit_price=price,
                    total=round(price * line.quantity, 2), channel=data.channel, date=when)
        db.add(sale)
        db.flush()
        if not dish.recipe:
            warnings.append(f"{dish.name}: sem ficha técnica, nada foi baixado do estoque")
        for comp_line in dish.recipe:
            comp = comp_line.component
            add_movement(db, comp, -comp_line.quantity * line.quantity, "venda",
                         unit_cost=current_cost(comp), when=when,
                         notes=f"{dish.name} × {line.quantity:g}", sale_id=sale.id)
        created += 1
        total += sale.total

    db.commit()
    negatives = [
        i.name for i in db.query(Item).filter(Item.kind != "venda", Item.stock < -1e-9).all()
    ]
    if negatives:
        warnings.append("Estoque negativo (falta registrar produção/compra?): " + ", ".join(negatives))
    return {"created": created, "total": round(total, 2), "warnings": warnings}


@router.get("")
def list_sales(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(Sale).order_by(Sale.date.desc(), Sale.id.desc()).limit(min(limit, 500)).all()
    return [
        {"id": s.id, "item_id": s.item_id, "item_name": s.item.name, "quantity": s.quantity,
         "unit_price": s.unit_price, "total": s.total, "channel": s.channel or "direta", "date": s.date}
        for s in rows
    ]


@router.delete("/{id}", status_code=204)
def undo_sale(id: int, db: Session = Depends(get_db)):
    """Desfaz uma venda lançada errado e devolve as porções ao estoque."""
    sale = db.get(Sale, id)
    if not sale:
        raise HTTPException(404, "Venda não encontrada")
    for mv in db.query(Movement).filter_by(sale_id=id).all():
        mv.item.stock -= mv.quantity
        db.delete(mv)
    db.delete(sale)
    db.commit()
