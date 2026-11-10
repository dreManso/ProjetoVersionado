"""
Regras de negócio da cozinha.

Três movimentos mudam o estoque:
  COMPRA    → entra o insumo (peso bruto) e o custo médio é recalculado.
  PRODUÇÃO  → consome insumos/subprodutos e gera outro item com o rendimento
              REAL (pesado ou contado). Perdas (gordura, água do descongelamento,
              cozimento) e ganhos (arroz, feijão) ficam embutidos no custo.
  VENDA     → baixa os componentes da ficha do prato, um nível só
              (as porções prontas), nunca o insumo cru.

Reposição: consumo médio das últimas 4 semanas (semana de 6 dias de trabalho),
multiplicado pelos dias de cobertura de cada item, descendo pela cadeia
(prato → porção → insumo) para montar a lista de produção e a de compras.
"""
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import Item, Movement, Sale, Setting

WINDOW_DAYS = 28
WORK_DAYS_PER_WEEK = 6
MIN_WORK_DAYS = 6   # com menos de 1 semana de histórico, divide por pelo menos 6 dias (evita média inflada)
EPS = 1e-9


# ── unidades ──────────────────────────────────────────────────────────────────

UNIT_FAMILY = {"kg": ("peso", 1000.0), "g": ("peso", 1.0),
               "L": ("volume", 1000.0), "mL": ("volume", 1.0), "un": ("unidade", 1.0)}


def convert_unit(quantity: float, from_unit, to_unit: str) -> float:
    """Converte g↔kg e mL↔L. Levanta ValueError entre famílias diferentes."""
    if not from_unit or from_unit == to_unit:
        return quantity
    a, b = UNIT_FAMILY.get(from_unit), UNIT_FAMILY.get(to_unit)
    if not a or not b or a[0] != b[0]:
        raise ValueError(f"não dá para converter {from_unit} em {to_unit}")
    return quantity * a[1] / b[1]


def item_units(item) -> list:
    """Unidades aceitas para um item: as da unidade de estoque e, se for porção com peso, as do peso."""
    fam = {"kg": ["kg", "g"], "g": ["g", "kg"], "L": ["L", "mL"], "mL": ["mL", "L"], "un": ["un"]}
    units = list(fam.get(item.unit, [item.unit]))
    if item.unit == "un" and item.portion_size and item.portion_unit:
        units += fam.get(item.portion_unit, [])
    return units


def to_stock_units(quantity: float, from_unit, item) -> float:
    """Quantidade digitada (ex.: 300 g de uma porção de 300 g) → unidade de estoque do item (1 un)."""
    if not from_unit or from_unit == item.unit:
        return quantity
    try:
        return convert_unit(quantity, from_unit, item.unit)
    except ValueError:
        if item.unit == "un" and item.portion_size and item.portion_unit:
            return convert_unit(quantity, from_unit, item.portion_unit) / item.portion_size
        raise


def from_stock_units(quantity: float, to_unit, item) -> float:
    """Inverso de to_stock_units (para exibir na unidade digitada)."""
    if not to_unit or to_unit == item.unit:
        return quantity
    try:
        return convert_unit(quantity, item.unit, to_unit)
    except ValueError:
        if item.unit == "un" and item.portion_size and item.portion_unit:
            return convert_unit(quantity * item.portion_size, item.portion_unit, to_unit)
        raise


# ── configurações e preços ────────────────────────────────────────────────────

DEFAULT_SETTINGS = {"ifood_fee_percent": 30.0}


def get_setting(db: Session, key: str) -> float:
    row = db.get(Setting, key)
    try:
        return float(row.value) if row else DEFAULT_SETTINGS[key]
    except ValueError:
        return DEFAULT_SETTINGS[key]


def ifood_price(direct_price, fee_percent: float):
    """Preço no iFood para receber o mesmo que na venda direta: direta ÷ (1 − taxa)."""
    if not direct_price:
        return None
    return round(direct_price / (1 - fee_percent / 100), 2)


def markup_percent(price, cost):
    """Lucro sobre o custo: (preço ÷ custo − 1) × 100."""
    if not price or not cost:
        return None
    return round((price / cost - 1) * 100, 1)


# ── datas e movimentos ────────────────────────────────────────────────────────

def to_datetime(day):
    """Data informada na tela → datetime. Hoje usa a hora atual."""
    if day is None or day == date.today():
        return datetime.now()
    return datetime.combine(day, time(12, 0))


def add_movement(db: Session, item: Item, quantity: float, type_: str, unit_cost=None,
                 when=None, notes=None, production_id=None, sale_id=None) -> Movement:
    item.stock = round((item.stock or 0.0) + quantity, 6) + 0.0   # sem sobras de arredondamento (-0,0000001)
    mv = Movement(
        item_id=item.id, type=type_, quantity=quantity, unit_cost=unit_cost,
        date=when or datetime.now(), notes=notes,
        production_id=production_id, sale_id=sale_id,
    )
    db.add(mv)
    return mv


def update_avg_cost(item: Item, quantity_in: float, value_in: float):
    """Custo médio ponderado. Chamar ANTES de somar a entrada no estoque."""
    base = max(item.stock or 0.0, 0.0)
    total = base + quantity_in
    if total > EPS:
        item.avg_cost = (base * (item.avg_cost or 0.0) + value_in) / total


# ── custo pela ficha técnica ──────────────────────────────────────────────────

def unit_cost(item: Item, _memo=None, _stack=None):
    """
    Custo de 1 unidade do item pela ficha técnica.
      compra   → custo médio das compras
      producao → soma dos componentes de uma receita ÷ rendimento
      venda    → soma dos componentes de 1 prato
    Retorna (custo | None, [pendências]).
    """
    memo = {} if _memo is None else _memo
    stack = set() if _stack is None else _stack
    if item.id in memo:
        return memo[item.id]
    if item.id in stack:
        raise ValueError(f"Ficha técnica circular envolvendo '{item.name}'")

    if item.kind == "compra":
        issues = [] if item.avg_cost > 0 else [f"{item.name}: sem custo (registre uma compra)"]
        result = (item.avg_cost, issues)
    else:
        stack.add(item.id)
        total, issues = 0.0, []
        for line in item.recipe:
            c, sub = unit_cost(line.component, memo, stack)
            issues += sub
            if c is not None:
                total += c * line.cost_quantity
        stack.discard(item.id)
        if not item.recipe:
            issues.append(f"{item.name}: ficha técnica vazia")
        if item.kind == "producao":
            if not item.yield_quantity:
                result = (None, issues + [f"{item.name}: rendimento não definido"])
            else:
                result = (total / item.yield_quantity, issues)
        else:
            result = (total, issues)

    result = (result[0], list(dict.fromkeys(result[1])))
    memo[item.id] = result
    return result


def cost_breakdown(item: Item) -> dict:
    memo = {}
    cost, issues = unit_cost(item, memo)
    lines = []
    for line in item.recipe:
        c, _ = unit_cost(line.component, memo)
        shown_unit = line.unit or line.component.unit
        try:
            shown_qty = from_stock_units(line.quantity, shown_unit, line.component)
        except ValueError:
            shown_unit, shown_qty = line.component.unit, line.quantity
        lines.append({
            "name": line.component.name,
            "kind": line.component.kind,
            "quantity": line.quantity,
            "cost_quantity": round(line.cost_quantity, 6),
            "loss_percent": line.effective_loss,
            "unit": line.component.unit,
            "display_quantity": round(shown_qty, 6),
            "display_unit": shown_unit,
            "unit_cost": None if c is None else round(c, 6),
            "total": None if c is None else round(c * line.cost_quantity, 4),
        })
    suggested = {}
    if item.kind == "venda" and cost:
        # Lucro sobre o custo (markup): preço = custo × (1 + lucro)
        for m in (100, 150, 200, 250):
            suggested[f"Lucro {m}%"] = round(cost * (1 + m / 100), 2)
    return {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "unit": item.unit,
        "yield_quantity": item.yield_quantity,
        "recipe_cost": round(sum(l["total"] or 0 for l in lines), 4),
        "unit_cost": None if cost is None else round(cost, 6),
        "avg_cost": item.avg_cost,
        "selling_price": item.selling_price,
        "cmv_percent": round(cost / item.selling_price * 100, 1)
        if (item.kind == "venda" and cost and item.selling_price) else None,
        "markup_percent": markup_percent(item.selling_price, cost) if item.kind == "venda" else None,
        "lines": lines,
        "issues": issues,
        "suggested_prices": suggested,
    }


def current_cost(item: Item) -> float:
    """Custo usado para valorizar uma saída de estoque."""
    if item.avg_cost and item.avg_cost > 0:
        return item.avg_cost
    c, _ = unit_cost(item)
    return c or 0.0


def creates_cycle(db: Session, parent_id: int, component_id: int) -> bool:
    """True se `component_id` já usa (direta ou indiretamente) `parent_id`."""
    stack, seen = [component_id], set()
    while stack:
        cid = stack.pop()
        if cid == parent_id:
            return True
        if cid in seen:
            continue
        seen.add(cid)
        comp = db.get(Item, cid)
        if comp:
            stack.extend(l.component_id for l in comp.recipe)
    return False


# ── reposição a partir das vendas ─────────────────────────────────────────────

def sales_history_days(db: Session, now=None) -> float:
    """Quantos dias de vendas lançadas existem dentro da janela de 4 semanas."""
    now = now or datetime.now()
    first = db.query(func.min(Sale.date)).scalar()
    if first is None:
        return 0.0
    span_start = max(now - timedelta(days=WINDOW_DAYS), first)
    return max(0.0, (now - span_start).total_seconds() / 86400)


def daily_sales(db: Session, now=None) -> dict:
    """Pratos vendidos por dia de trabalho, nas últimas 4 semanas
    (com pouco histórico, divide por pelo menos MIN_WORK_DAYS)."""
    now = now or datetime.now()
    start = now - timedelta(days=WINDOW_DAYS)
    work_days = max(MIN_WORK_DAYS, sales_history_days(db, now) * WORK_DAYS_PER_WEEK / 7)
    rows = (
        db.query(Sale.item_id, func.sum(Sale.quantity))
        .filter(Sale.date >= start)
        .group_by(Sale.item_id)
        .all()
    )
    return {item_id: total / work_days for item_id, total in rows if total}


def _round_up(qty: float, unit: str) -> float:
    if unit == "un":
        return float(math.ceil(qty - EPS))
    return round(math.ceil(qty * 1000 - EPS) / 1000, 3)


def _topological(items_by_id: dict) -> list:
    """Ordena para que quem consome venha antes de quem é consumido."""
    order, seen = [], set()

    def visit(it):
        if it.id in seen:
            return
        seen.add(it.id)
        for line in it.recipe:
            comp = items_by_id.get(line.component_id)
            if comp:
                visit(comp)
        order.append(it)

    for it in items_by_id.values():
        visit(it)
    return list(reversed(order))


def replenishment(db: Session, now=None) -> dict:
    """
    A demanda nasce nos PRATOS VENDIDOS:
      1. média de pratos vendidos por dia (últimas 4 semanas);
      2. pelas fichas, vira consumo diário de porções/subprodutos e insumos
         (prato → porção → insumo);
      3. estoque na cadeia = estoque do item + o que já está pronto nos itens
         feitos com ele (feijão porcionado conta como feijão);
      4. alvo = consumo/dia × dias de cobertura + estoque de segurança;
         falta = alvo − estoque na cadeia, e nunca menos do que a produção
         sugerida vai tirar do item agora.
    Itens produzidos viram ordem de produção (respeitando o lote mínimo); a lista
    de compras é arredondada para a embalagem do fornecedor.
    """
    items = db.query(Item).filter(Item.active.is_(True), Item.kind != "venda").all()
    by_id = {i.id: i for i in items}
    dishes = db.query(Item).filter(Item.active.is_(True), Item.kind == "venda").all()
    order = _topological(by_id)   # quem consome antes de quem é consumido

    # 1–2. consumo diário vindo das vendas, descendo pelas fichas
    sold = daily_sales(db, now)
    demand = defaultdict(float)
    for d in dishes:
        rate = sold.get(d.id, 0.0)
        for line in d.recipe if rate else []:
            demand[line.component_id] += rate * line.quantity
    for it in order:
        if it.kind == "producao" and it.yield_quantity and demand[it.id]:
            for line in it.recipe:
                demand[line.component_id] += demand[it.id] * line.quantity / it.yield_quantity

    # 3. estoque na cadeia (o item + o equivalente já transformado em itens produzidos)
    downstream = defaultdict(float)
    chain = {}
    for it in order:
        chain[it.id] = it.stock + downstream[it.id]
        if it.kind == "producao" and it.yield_quantity:
            for line in it.recipe:
                downstream[line.component_id] += max(chain[it.id], 0.0) * line.quantity / it.yield_quantity

    # 4. produção e compras
    projected = {i.id: i.stock for i in items}
    for_production = defaultdict(float)
    produce, buy, warnings = [], [], []
    for it in order:
        d = demand.get(it.id, 0.0)
        target = d * it.coverage_days + it.min_stock
        need = max(target - chain[it.id], -projected[it.id])
        if need <= EPS:
            continue
        row = {
            "id": it.id,
            "name": it.name,
            "unit": it.unit,
            "stock": round(it.stock, 3),
            "chain_stock": round(chain[it.id], 3),
            "daily": round(d, 3),
            "coverage_days": it.coverage_days,
            "min_stock": it.min_stock,
            "target": round(target, 3),
            "for_production": round(for_production[it.id], 3),
        }
        if it.kind == "producao":
            if not it.yield_quantity:
                warnings.append(f"{it.name}: defina o rendimento para calcular a produção")
                continue
            qty = _round_up(max(need, it.min_batch or 0.0), it.unit)
            scale = qty / it.yield_quantity
            inputs = []
            for line in it.recipe:
                q = line.quantity * scale
                if line.component_id in projected:
                    projected[line.component_id] -= q
                    for_production[line.component_id] += q
                inputs.append({"name": line.component.name, "quantity": round(q, 3),
                               "unit": line.component.unit})
            row.update(suggested=qty, batches=round(scale, 2), inputs=inputs)
            produce.append(row)
        else:
            if it.pack_size:
                packs = math.ceil(need / it.pack_size - EPS)
                qty = packs * it.pack_size
                row.update(packs=packs, pack_label=it.pack_label or "emb.", pack_size=it.pack_size)
            else:
                qty = _round_up(need, it.unit)
            row.update(suggested=round(qty, 3), estimated_cost=round(qty * it.avg_cost, 2))
            buy.append(row)

    return {
        "produce": produce,
        "buy": buy,
        "buy_total": round(sum(r["estimated_cost"] for r in buy), 2),
        "warnings": warnings,
        "window_days": WINDOW_DAYS,
        "history_days": round(sales_history_days(db, now), 1),
        "has_sales": bool(sold),
        "min_work_days": MIN_WORK_DAYS,
        "work_days_per_week": WORK_DAYS_PER_WEEK,
    }
