from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Item, Movement, Production, Sale
from ..services import replenishment

router = APIRouter()


@router.get("/replenishment")
def get_replenishment(db: Session = Depends(get_db)):
    return replenishment(db)


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    today = datetime.combine(date.today(), time.min)
    sales_today = db.query(func.coalesce(func.sum(Sale.total), 0.0),
                           func.coalesce(func.sum(Sale.quantity), 0.0)).filter(Sale.date >= today).one()
    stock_items = db.query(Item).filter(Item.kind != "venda", Item.active.is_(True)).order_by(Item.name).all()
    negative = [{"id": i.id, "name": i.name, "stock": i.stock, "unit": i.unit}
                for i in stock_items if i.stock < -1e-9]
    low = [{"id": i.id, "name": i.name, "stock": i.stock, "min_stock": i.min_stock, "unit": i.unit}
           for i in stock_items if 0 <= i.stock < i.min_stock]
    rep = replenishment(db)

    prods = db.query(Production).order_by(Production.date.desc()).limit(20).all()
    off_yield = []
    for p in prods:
        if p.expected_output:
            dev = (p.output_quantity / p.expected_output - 1) * 100
            if abs(dev) >= 5:
                off_yield.append({"item_name": p.item.name, "date": p.date, "unit": p.item.unit,
                                  "output": p.output_quantity, "expected": round(p.expected_output, 3),
                                  "deviation_percent": round(dev, 1)})

    adjust_loss = db.query(func.coalesce(func.sum(Movement.quantity * Movement.unit_cost), 0.0)).filter(
        Movement.type == "ajuste", Movement.quantity < 0
    ).scalar()

    return {
        "sales_today_total": round(sales_today[0], 2),
        "sales_today_count": sales_today[1],
        "negative": negative,
        "low": low,
        "to_produce": len(rep["produce"]),
        "to_buy": len(rep["buy"]),
        "buy_total": rep["buy_total"],
        "off_yield": off_yield[:8],
        "adjust_loss_value": round(-adjust_loss, 2),
    }
