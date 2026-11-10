"""
Importa os cadastros da PRIMEIRA versão do app (arquivo restaurante.db)
para a versão atual (arquivo cozinha.db).

Uso:  python importar_v1.py                 (procura restaurante.db nesta pasta)
      python importar_v1.py C:\\caminho\\restaurante.db

O que é importado:
  ingredientes                     → itens COMPRADOS (custo e saldo de estoque)
  preparações usadas em outras     → itens PRODUZIDOS (ficha e rendimento)
  demais preparações               → PRATOS do cardápio (ficha e preço)
  gramas/quilos e mL/litros        → convertidos para a unidade de cada item

Não é importado: o histórico de vendas e de movimentações. A primeira versão
dava baixa direto no ingrediente cru, então esse histórico não serve para as
médias da versão nova. O saldo atual de cada ingrediente é importado.

O arquivo restaurante.db não é alterado.
"""
import sqlite3
import sys
from pathlib import Path

from fastapi import HTTPException

from app.database import SessionLocal, init_db
from app.models import Item
from app.routers.items import create_item
from app.routers.stock import adjust
from app.schemas import AdjustIn, ItemIn

UNITS = ("kg", "g", "L", "mL", "un")
FAMILY = {"kg": ("peso", 1000), "g": ("peso", 1), "L": ("volume", 1000), "mL": ("volume", 1)}
REPORT = Path("relatorio_importacao.txt")

avisos = []


def aviso(msg):
    avisos.append(msg)


def unidade_nova(u, contexto):
    """Unidade da versão antiga → unidade aceita na nova."""
    if u in UNITS:
        return u
    if u and u.lower() in ("l", "litro", "litros"):
        return "L"
    if u and u.lower() in ("ml",):
        return "mL"
    if u:
        aviso(f"{contexto}: unidade '{u}' virou 'un'. Confira.")
    return "un"


def converter(qtd, de, para):
    """Converte quantidade entre unidades da mesma família. None se não der."""
    if de == para:
        return qtd
    a, b = FAMILY.get(de), FAMILY.get(para)
    if a and b and a[0] == b[0]:
        return qtd * a[1] / b[1]
    return None


def main():
    origem = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("restaurante.db")
    if not origem.exists():
        raise SystemExit(f"Não encontrei '{origem}'. Copie o restaurante.db da versão antiga para "
                         f"esta pasta ou informe o caminho: python importar_v1.py C:\\caminho\\restaurante.db")

    old = sqlite3.connect(origem)
    old.row_factory = sqlite3.Row
    try:
        ingredientes = old.execute("SELECT * FROM ingredients ORDER BY id").fetchall()
        pratos = old.execute("SELECT * FROM dishes ORDER BY id").fetchall()
        comps = old.execute("SELECT * FROM dish_components ORDER BY id").fetchall()
        n_vendas = old.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    except sqlite3.DatabaseError as e:
        raise SystemExit(f"'{origem}' não parece ser o banco da primeira versão ({e}).")

    init_db()
    db = SessionLocal()
    if db.query(Item).count():
        raise SystemExit("O cozinha.db já tem itens (talvez o exemplo do seed.py). "
                         "Feche o programa, apague o cozinha.db e rode este importador de novo.")

    usados_como_sub = {c["sub_dish_id"] for c in comps if c["sub_dish_id"]}
    comps_por_prato = {}
    for c in comps:
        comps_por_prato.setdefault(c["dish_id"], []).append(c)

    nomes_usados = set()

    def nome_unico(nome):
        base = (nome or "Sem nome").strip()[:110]
        n, i = base, 2
        while n.lower() in nomes_usados:
            n, i = f"{base} ({i})", i + 1
        if n != base:
            aviso(f"Nome repetido '{base}' foi importado como '{n}'.")
        nomes_usados.add(n.lower())
        return n

    novo_ing, novo_prep = {}, {}   # id antigo → (id novo, unidade nova)

    # 1. Ingredientes → comprados
    for ing in ingredientes:
        nome = nome_unico(ing["name"])
        unit = unidade_nova(ing["unit"], f"Ingrediente '{nome}'")
        item = create_item(ItemIn(name=nome, kind="compra", unit=unit,
                                  avg_cost=max(ing["cost_per_unit"] or 0, 0),
                                  min_stock=max(ing["min_stock"] or 0, 0)), db)
        novo_ing[ing["id"]] = (item["id"], unit, ing["unit"])
        saldo = ing["stock_quantity"] or 0
        if saldo < 0:
            aviso(f"'{nome}' estava com estoque negativo ({saldo:g}); entrou zerado. Faça uma contagem.")
        if saldo > 0:
            adjust(AdjustIn(item_id=item["id"], counted_quantity=saldo,
                            notes="Saldo importado da versão anterior"), db)

    def linha(c, dono):
        """Componente antigo → linha de ficha nova (com conversão de unidade)."""
        if c["ingredient_id"]:
            alvo = novo_ing.get(c["ingredient_id"])
        else:
            alvo = novo_prep.get(c["sub_dish_id"])
        if not alvo:
            return None
        item_id, unit, unit_antiga = alvo
        q = c["quantity"] if c["unit"] == unit_antiga else converter(c["quantity"], c["unit"], unit)
        if q is None:
            q = c["quantity"]
            aviso(f"Ficha de '{dono}': componente em '{c['unit']}' e estoque em '{unit}'. "
                  f"Mantive {c['quantity']:g}. Confira.")
        return {"component_id": item_id, "quantity": q}

    # 2. Preparações usadas dentro de outras → produzidos (subprodutos antes de quem os usa)
    pendentes = [p for p in pratos if p["id"] in usados_como_sub]
    while pendentes:
        prontos = [p for p in pendentes
                   if all(not c["sub_dish_id"] or c["sub_dish_id"] in novo_prep
                          for c in comps_por_prato.get(p["id"], []))]
        if not prontos:  # ciclo na versão antiga
            prontos = pendentes[:1]
            aviso(f"'{prontos[0]['name']}' tinha ficha circular. Algum componente pode ter ficado de fora.")
        for p in prontos:
            nome = nome_unico(p["name"])
            unit = unidade_nova(p["yield_unit"], f"Rendimento de '{nome}'")
            ficha = [l for l in (linha(c, nome) for c in comps_por_prato.get(p["id"], [])) if l]
            ids = set()
            ficha = [l for l in ficha if not (l["component_id"] in ids or ids.add(l["component_id"]))]
            if not p["yield_quantity"]:
                aviso(f"'{nome}' está sem rendimento. Defina em Itens e fichas.")
            notas = "\n\n".join(x for x in (p["description"], p["preparation_steps"]) if x) or None
            item = create_item(ItemIn(name=nome, kind="producao", unit=unit,
                                      yield_quantity=p["yield_quantity"] or None,
                                      notes=notas, recipe=ficha), db)
            novo_prep[p["id"]] = (item["id"], unit, p["yield_unit"])
            if p["is_sellable"] and p["selling_price"]:
                if unit == "un":
                    create_item(ItemIn(name=nome_unico(f"{nome} (venda avulsa)"), kind="venda",
                                       selling_price=p["selling_price"],
                                       recipe=[{"component_id": item["id"], "quantity": 1}]), db)
                    aviso(f"'{nome}' também era vendido sozinho: criei o prato '{nome} (venda avulsa)' com 1 un.")
                else:
                    aviso(f"'{nome}' também era vendido sozinho, mas rende em {unit}. Cadastre o prato "
                          f"(ex.: pote de 500 mL) em Itens e fichas, por R$ {p['selling_price']:.2f}.")
        pendentes = [p for p in pendentes if p["id"] not in novo_prep]

    # 3. Demais preparações → pratos (ficha por 1 prato)
    for p in pratos:
        if p["id"] in usados_como_sub:
            continue
        nome = nome_unico(p["name"])
        rend = p["yield_quantity"] or 1
        ficha = []
        for c in comps_por_prato.get(p["id"], []):
            l = linha(c, nome)
            if l:
                l["quantity"] /= rend
                if l["component_id"] not in {x["component_id"] for x in ficha}:
                    ficha.append(l)
        if rend != 1:
            aviso(f"'{nome}' rendia {rend:g} {p['yield_unit'] or 'porções'}: a ficha foi dividida para 1 prato.")
        if not p["is_sellable"]:
            aviso(f"'{nome}' não estava marcado como vendável e não é usado em outra ficha. "
                  f"Importei como prato inativo.")
        notas = "\n\n".join(x for x in (p["description"], p["preparation_steps"]) if x) or None
        create_item(ItemIn(name=nome, kind="venda", selling_price=p["selling_price"],
                           active=bool(p["is_sellable"]), notes=notas, recipe=ficha), db)

    if n_vendas:
        aviso(f"{n_vendas} venda(s) antigas não foram importadas: a primeira versão dava baixa no "
              f"ingrediente cru, e o histórico distorceria as médias. Os saldos atuais foram importados.")

    db.close()
    resumo = (f"Importado de {origem}:\n"
              f"  {len(novo_ing)} ingrediente(s) → comprados\n"
              f"  {len(novo_prep)} preparação(ões) → produzidos\n"
              f"  {len(pratos) - len(novo_prep)} preparação(ões) → pratos\n")
    texto = resumo + ("\nConfira:\n" + "\n".join(f"  - {a}" for a in avisos) if avisos else "\nSem pendências.")
    REPORT.write_text(texto + "\n", encoding="utf-8")
    print(texto)
    print(f"\n(Relatório salvo em {REPORT.resolve()})")


if __name__ == "__main__":
    try:
        main()
    except HTTPException as e:
        raise SystemExit(f"Erro ao importar: {e.detail}")
