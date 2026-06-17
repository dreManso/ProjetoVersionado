"""
Lógica de cálculo de custo e de baixa de estoque.

Custo unitário de uma preparação:
    custo_unitário = soma_de_custos_dos_componentes / rendimento

Quando um subproduto é usado como componente:
    custo_componente = (custo_total_subproduto / rendimento_subproduto) × quantidade_usada

Baixa de estoque: desce recursivamente até os ingredientes brutos.
"""

from sqlalchemy.orm import Session
from .models import Dish, Ingredient


def calculate_dish_cost(dish_id: int, db: Session, _visited: set = None) -> dict:
    """
    Retorna:
      {
        "total_cost": float,
        "cost_per_yield_unit": float | None,  # None se rendimento não definido
        "is_complete": bool,                   # False se algum rendimento falta
        "components": [ComponentCostDetail]
      }
    """
    if _visited is None:
        _visited = set()

    if dish_id in _visited:
        raise ValueError("Dependência circular detectada nas preparações")
    _visited.add(dish_id)

    dish = db.get(Dish, dish_id)
    if not dish:
        raise ValueError(f"Preparação {dish_id} não encontrada")

    total_cost = 0.0
    components_detail = []
    is_complete = True

    for comp in dish.components:
        if comp.ingredient_id is not None:
            ing = comp.ingredient
            component_cost = ing.cost_per_unit * comp.quantity
            total_cost += component_cost
            components_detail.append({
                "type": "ingredient",
                "name": ing.name,
                "quantity": comp.quantity,
                "unit": comp.unit,
                "cost_per_unit": ing.cost_per_unit,
                "total": round(component_cost, 4),
                "is_complete": True,
                "error": None,
            })

        elif comp.sub_dish_id is not None:
            sub = comp.sub_dish

            if not sub.yield_quantity:
                is_complete = False
                components_detail.append({
                    "type": "sub_dish",
                    "name": sub.name,
                    "quantity": comp.quantity,
                    "unit": comp.unit,
                    "cost_per_unit": None,
                    "total": 0.0,
                    "is_complete": False,
                    "error": f"Rendimento de '{sub.name}' não definido",
                })
                continue

            sub_result = calculate_dish_cost(sub.id, db, _visited.copy())

            if not sub_result["is_complete"]:
                is_complete = False

            # custo por unidade do rendimento do subproduto
            cost_per_yield = sub_result["total_cost"] / sub.yield_quantity
            component_cost = cost_per_yield * comp.quantity
            total_cost += component_cost

            components_detail.append({
                "type": "sub_dish",
                "name": sub.name,
                "quantity": comp.quantity,
                "unit": comp.unit,
                "cost_per_unit": round(cost_per_yield, 4),
                "total": round(component_cost, 4),
                "is_complete": sub_result["is_complete"],
                "error": None if sub_result["is_complete"] else "Sub-receita incompleta",
            })

    # custo por unidade de rendimento deste prato
    cost_per_yield_unit = None
    if dish.yield_quantity and is_complete:
        cost_per_yield_unit = round(total_cost / dish.yield_quantity, 4)

    # prato é considerado completo se tem rendimento E todos os sub têm rendimento
    is_complete = is_complete and bool(dish.yield_quantity)

    return {
        "total_cost": round(total_cost, 4),
        "cost_per_yield_unit": cost_per_yield_unit,
        "is_complete": is_complete,
        "components": components_detail,
    }


def get_raw_ingredients_needed(dish: Dish, needed_quantity: float, db: Session, _visited: set = None) -> dict:
    """
    Retorna {ingredient_id: quantidade_necessária} de matérias-primas brutas
    para produzir `needed_quantity` unidades de `dish`.

    Desce recursivamente por subprodutos até chegar nos ingredientes brutos.
    A quantidade é proporcional ao rendimento de cada nível da receita.
    """
    if _visited is None:
        _visited = set()

    if dish.id in _visited:
        raise ValueError("Dependência circular detectada")
    _visited.add(dish.id)

    yield_qty = dish.yield_quantity or 1.0
    scale = needed_quantity / yield_qty

    result: dict[int, float] = {}

    for comp in dish.components:
        qty_needed = comp.quantity * scale

        if comp.ingredient_id is not None:
            result[comp.ingredient_id] = result.get(comp.ingredient_id, 0.0) + qty_needed

        elif comp.sub_dish_id is not None:
            sub = comp.sub_dish
            sub_raw = get_raw_ingredients_needed(sub, qty_needed, db, _visited.copy())
            for ing_id, qty in sub_raw.items():
                result[ing_id] = result.get(ing_id, 0.0) + qty

    return result
