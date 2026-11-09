from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Item, Production
from ..schemas import ProductionIn
from ..services import add_movement, current_cost, to_datetime, update_avg_cost

router = APIRouter()


def _expected_output(item: Item, actual_inputs: dict):
    """Rendimento esperado pela ficha, proporcional ao insumo principal (1ª linha)."""
    if not item.recipe or not item.yield_quantity:
        return None
    main = item.recipe[0]
    used = actual_inputs.get(main.component_id)
    if not used:
        return None
    return item.yield_quantity * used / main.quantity


def _serialize(p: Production) -> dict:
    deviation = None
    if p.expected_output:
        deviation = round((p.output_quantity / p.expected_output - 1) * 100, 1)
    return {
        "id": p.id,
        "item_id": p.item_id,
        "item_name": p.item.name,
        "unit": p.item.unit,
        "output_quantity": p.output_quantity,
        "expected_output": None if p.expected_output is None else round(p.expected_output, 3),
        "deviation_percent": deviation,
        "input_cost": round(p.input_cost, 2),
        "unit_cost": round(p.input_cost / p.output_quantity, 4),
        "date": p.date,
        "notes": p.notes,
    }


@router.post("", status_code=201)
def register_production(data: ProductionIn, db: Session = Depends(get_db)):
    """
    Produção/fracionamento: baixa o que entrou (peso bruto real) e dá entrada
    no que saiu (rendimento real). O custo real do lote vai para o item.
    """
    item = db.get(Item, data.item_id)
    if not item or item.kind != "producao":
        raise HTTPException(400, "Escolha um item do tipo 'produzido'")

    inputs, actual = [], {}
    for line in data.inputs:
        comp = db.get(Item, line.item_id)
        if not comp or comp.kind == "venda" or comp.id == item.id:
            raise HTTPException(400, f"Insumo inválido: {line.item_id}")
        inputs.append((comp, line.quantity))
        actual[comp.id] = actual.get(comp.id, 0.0) + line.quantity

    when = to_datetime(data.day)
    input_cost = sum(current_cost(c) * q for c, q in inputs)
    prod = Production(
        item_id=item.id,
        output_quantity=data.output_quantity,
        expected_output=_expected_output(item, actual),
        input_cost=input_cost,
        date=when,
        notes=data.notes,
    )
    db.add(prod)
    db.flush()

    for comp, q in inputs:
        add_movement(db, comp, -q, "producao_consumo", unit_cost=current_cost(comp),
                     when=when, notes=f"Produção de {item.name}", production_id=prod.id)

    update_avg_cost(item, data.output_quantity, input_cost)
    add_movement(db, item, data.output_quantity, "producao_entrada",
                 unit_cost=input_cost / data.output_quantity, when=when,
                 notes=data.notes, production_id=prod.id)
    db.commit()
    db.refresh(prod)
    return _serialize(prod)


@router.get("")
def list_productions(limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(Production)
        .order_by(Production.date.desc(), Production.id.desc())
        .limit(min(limit, 500))
        .all()
    )
    return [_serialize(p) for p in rows]
