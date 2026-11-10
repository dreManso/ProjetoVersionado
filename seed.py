"""
Carrega DADOS DE EXEMPLO (preços e quantidades fictícios) para testar o app.
Uso:  python seed.py
Só roda com o banco vazio. Para recomeçar, apague o arquivo cozinha.db.
"""
from datetime import date, timedelta

from app.database import SessionLocal, init_db
from app.models import Item
from app.routers.items import create_item
from app.routers.production import register_production
from app.routers.sales import register_sales
from app.routers.stock import purchase
from app.schemas import ItemIn, ProductionIn, PurchaseIn, SalesIn

init_db()
db = SessionLocal()
if db.query(Item).count():
    raise SystemExit("O banco já tem itens. Apague cozinha.db para carregar o exemplo.")

ids = {}


def add(name, kind, unit="un", recipe=(), **kw):
    data = ItemIn(name=name, kind=kind, unit=unit,
                  recipe=[{"component_id": ids[c], "quantity": q} for c, q in recipe], **kw)
    ids[name] = create_item(data, db)["id"]


def day(n):
    return date.today() - timedelta(days=n)


# ── comprados ──
add("Arroz cru", "compra", "kg", pack_size=5, pack_label="fardo")
add("Feijão cru", "compra", "kg", pack_size=1, pack_label="pacote")
add("Coxão mole (peça)", "compra", "kg", coverage_days=6)
add("Peito de frango", "compra", "kg", coverage_days=6)
add("Batata palito congelada", "compra", "kg", pack_size=2, pack_label="pacote")
add("Batata para nhoque", "compra", "kg")
add("Farinha de trigo", "compra", "kg", pack_size=5, pack_label="pacote")
add("Farinha de rosca", "compra", "kg", pack_size=1, pack_label="pacote")
add("Ovo", "compra", "un", pack_size=30, pack_label="bandeja")
add("Creme de leite", "compra", "un", pack_size=27, pack_label="caixa")
add("Molho de tomate pronto", "compra", "kg", pack_size=2, pack_label="bag")
add("Queijo muçarela", "compra", "kg")
add("Óleo", "compra", "L", pack_size=0.9, pack_label="garrafa")
add("Embalagem marmita", "compra", "un", pack_size=100, pack_label="pacote", min_stock=50)
add("Lacre", "compra", "un", pack_size=500, pack_label="rolo", min_stock=100)
add("Saco de entrega", "compra", "un", pack_size=100, pack_label="pacote", min_stock=50)

# ── produzidos (rendimentos de exemplo) ──
add("Arroz porção 250g", "producao", "un", yield_quantity=10, min_batch=20, coverage_days=2,
    recipe=[("Arroz cru", 1)])
add("Feijão porção 200g", "producao", "un", yield_quantity=12, min_batch=24, coverage_days=3,
    recipe=[("Feijão cru", 1)])
add("Bife coxão mole 129g", "producao", "un", yield_quantity=6, min_batch=30, coverage_days=12,
    recipe=[("Coxão mole (peça)", 1)], notes="Limpar gordura e nervos; porcionar 129 g; congelar")
add("Bife de frango", "producao", "un", yield_quantity=7, coverage_days=6,
    recipe=[("Peito de frango", 1)])
add("Tiras de frango", "producao", "kg", yield_quantity=0.9, coverage_days=3,
    recipe=[("Bife de frango", 7)])
add("Frango desfiado", "producao", "kg", yield_quantity=0.55, coverage_days=4,
    recipe=[("Peito de frango", 1)], notes="Descongelar, cozinhar e desfiar")
add("Batata porção 200g", "producao", "un", yield_quantity=10, coverage_days=3,
    recipe=[("Batata palito congelada", 2)])
add("Nhoque porção 300g", "producao", "un", yield_quantity=8, min_batch=24, coverage_days=12,
    recipe=[("Batata para nhoque", 2), ("Farinha de trigo", 0.6), ("Ovo", 2)])

# ── pratos ──
ENTREGA = [("Embalagem marmita", 1), ("Lacre", 1), ("Saco de entrega", 1)]
add("Estrogonofe de carne", "venda", selling_price=42, recipe=[
    ("Bife coxão mole 129g", 1), ("Creme de leite", 0.5), ("Arroz porção 250g", 1), *ENTREGA])
add("Bife à milanesa", "venda", selling_price=38, recipe=[
    ("Bife coxão mole 129g", 1), ("Farinha de rosca", 0.04), ("Ovo", 1), ("Óleo", 0.05),
    ("Arroz porção 250g", 1), ("Feijão porção 200g", 1), ("Batata porção 200g", 1), *ENTREGA])
add("Parmegiana", "venda", selling_price=46, recipe=[
    ("Bife coxão mole 129g", 1), ("Farinha de rosca", 0.04), ("Ovo", 1), ("Óleo", 0.05),
    ("Molho de tomate pronto", 0.12), ("Queijo muçarela", 0.06), ("Arroz porção 250g", 1),
    ("Batata porção 200g", 1), *ENTREGA])
add("Estrogonofe de frango", "venda", selling_price=36, recipe=[
    ("Tiras de frango", 0.15), ("Creme de leite", 0.5), ("Arroz porção 250g", 1), *ENTREGA])
add("Risoto de frango", "venda", selling_price=39, recipe=[
    ("Frango desfiado", 0.12), ("Arroz cru", 0.1), ("Creme de leite", 0.5), *ENTREGA])
add("Nhoque ao sugo", "venda", selling_price=34, recipe=[
    ("Nhoque porção 300g", 1), ("Molho de tomate pronto", 0.15), *ENTREGA])
add("Nhoque à parmegiana", "venda", selling_price=48, recipe=[
    ("Nhoque porção 300g", 1), ("Bife coxão mole 129g", 1), ("Farinha de rosca", 0.04),
    ("Ovo", 1), ("Molho de tomate pronto", 0.15), ("Queijo muçarela", 0.06), *ENTREGA])
add("Batata frita grande", "venda", selling_price=22, recipe=[
    ("Batata porção 200g", 2), ("Óleo", 0.1), ("Saco de entrega", 1)])
add("Batata frita pequena", "venda", selling_price=13, recipe=[
    ("Batata porção 200g", 1), ("Óleo", 0.05), ("Saco de entrega", 1)])

# ── compras iniciais (há 20 dias) ──
for name, q, total in [
    ("Arroz cru", 30, 180), ("Feijão cru", 10, 85), ("Coxão mole (peça)", 25, 950),
    ("Peito de frango", 20, 360), ("Batata palito congelada", 40, 440),
    ("Batata para nhoque", 10, 45), ("Farinha de trigo", 5, 25), ("Farinha de rosca", 3, 30),
    ("Ovo", 180, 144), ("Creme de leite", 81, 283.5), ("Molho de tomate pronto", 16, 128),
    ("Queijo muçarela", 5, 210), ("Óleo", 9, 81), ("Embalagem marmita", 600, 540),
    ("Lacre", 1000, 100), ("Saco de entrega", 700, 210),
]:
    purchase(PurchaseIn(item_id=ids[name], quantity=q, total_price=total, day=day(20)), db)


def produce(name, out, inputs, n):
    register_production(ProductionIn(item_id=ids[name], output_quantity=out, day=day(n),
                                     inputs=[{"item_id": ids[c], "quantity": q} for c, q in inputs]), db)


# ── produções (rendimento real varia um pouco da ficha) ──
produce("Bife coxão mole 129g", 118, [("Coxão mole (peça)", 21)], 19)   # ficha: 126
produce("Arroz porção 250g", 150, [("Arroz cru", 15)], 19)
produce("Feijão porção 200g", 60, [("Feijão cru", 5)], 19)
produce("Bife de frango", 70, [("Peito de frango", 10)], 19)
produce("Tiras de frango", 6.1, [("Bife de frango", 49)], 18)
produce("Frango desfiado", 5.2, [("Peito de frango", 10)], 18)          # ficha: 5,5
produce("Batata porção 200g", 170, [("Batata palito congelada", 34)], 19)
produce("Nhoque porção 300g", 38, [("Batata para nhoque", 10), ("Farinha de trigo", 3), ("Ovo", 10)], 19)

# ── segunda rodada (há 10 dias) ──
for name, q, total in [
    ("Coxão mole (peça)", 20, 780), ("Batata palito congelada", 30, 330), ("Batata para nhoque", 6, 27),
    ("Creme de leite", 54, 189), ("Óleo", 9, 81), ("Farinha de rosca", 3, 30), ("Arroz cru", 10, 60),
    ("Peito de frango", 10, 185), ("Molho de tomate pronto", 4, 32), ("Queijo muçarela", 2, 86),
]:
    purchase(PurchaseIn(item_id=ids[name], quantity=q, total_price=total, day=day(10)), db)
produce("Arroz porção 250g", 130, [("Arroz cru", 13)], 10)
produce("Bife coxão mole 129g", 112, [("Coxão mole (peça)", 19)], 9)    # ficha: 114
produce("Batata porção 200g", 145, [("Batata palito congelada", 29)], 9)
produce("Nhoque porção 300g", 23, [("Batata para nhoque", 6), ("Farinha de trigo", 1.8), ("Ovo", 6)], 9)
produce("Bife de frango", 69, [("Peito de frango", 10)], 9)
produce("Tiras de frango", 6, [("Bife de frango", 49)], 8)

# ── vendas dos últimos 18 dias (folga às segundas) ──
MIX = {"Estrogonofe de carne": 4, "Bife à milanesa": 2, "Parmegiana": 3, "Estrogonofe de frango": 3,
       "Risoto de frango": 2, "Nhoque ao sugo": 1, "Nhoque à parmegiana": 1,
       "Batata frita grande": 2, "Batata frita pequena": 2}
for n in range(18, 0, -1):
    d = day(n)
    if d.weekday() == 0:
        continue
    bump = 1 if d.weekday() >= 4 else 0
    register_sales(SalesIn(day=d, lines=[{"item_id": ids[k], "quantity": v + bump} for k, v in MIX.items()]), db)

db.close()
print("Exemplo carregado. Rode: python run.py e abra http://localhost:8000")
