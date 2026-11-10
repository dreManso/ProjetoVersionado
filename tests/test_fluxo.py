"""
Testes do fluxo da cozinha: compra → produção → venda → reposição.
Rodar: python -m pytest -q
"""
import os
import tempfile

import pytest

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["COZINHA_DB"] = f"sqlite:///{_db.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def item(**kw):
    r = client.post("/api/items", json=kw)
    assert r.status_code == 201, r.text
    return r.json()


def get(id):
    return client.get(f"/api/items/{id}").json()


def montar_coxao():
    coxao = item(name="Coxão mole (peça)", kind="compra", unit="kg")
    emb = item(name="Embalagem", kind="compra", unit="un")
    bife = item(name="Bife coxão 129g", kind="producao", unit="un", yield_quantity=6,
                recipe=[{"component_id": coxao["id"], "quantity": 1}])
    estrog = item(name="Estrogonofe", kind="venda", selling_price=40,
                  recipe=[{"component_id": bife["id"], "quantity": 1},
                          {"component_id": emb["id"], "quantity": 1}])
    return coxao, emb, bife, estrog


def test_compra_atualiza_custo_medio():
    coxao, *_ = montar_coxao()
    client.post("/api/stock/purchase", json={"item_id": coxao["id"], "quantity": 10, "total_price": 300})
    client.post("/api/stock/purchase", json={"item_id": coxao["id"], "quantity": 10, "total_price": 400})
    c = get(coxao["id"])
    assert c["stock"] == 20
    assert c["avg_cost"] == pytest.approx(35.0)


def test_producao_usa_rendimento_real_e_calcula_desvio():
    coxao, emb, bife, _ = montar_coxao()
    client.post("/api/stock/purchase", json={"item_id": coxao["id"], "quantity": 10, "total_price": 360})
    # 5 kg brutos deveriam render 30 bifes; rendeu 27 (gordura, aparas)
    r = client.post("/api/production", json={
        "item_id": bife["id"], "output_quantity": 27,
        "inputs": [{"item_id": coxao["id"], "quantity": 5}],
    })
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["expected_output"] == pytest.approx(30)
    assert p["deviation_percent"] == pytest.approx(-10.0)
    assert p["unit_cost"] == pytest.approx(180 / 27, rel=1e-3)
    assert get(coxao["id"])["stock"] == pytest.approx(5)
    assert get(bife["id"])["stock"] == pytest.approx(27)
    assert get(bife["id"])["avg_cost"] == pytest.approx(180 / 27, rel=1e-3)


def test_producao_com_ganho_de_peso_arroz():
    arroz = item(name="Arroz cru", kind="compra", unit="kg")
    porcao = item(name="Arroz porção 250g", kind="producao", unit="un", yield_quantity=10,
                  recipe=[{"component_id": arroz["id"], "quantity": 1}])
    client.post("/api/stock/purchase", json={"item_id": arroz["id"], "quantity": 5, "total_price": 30})
    p = client.post("/api/production", json={
        "item_id": porcao["id"], "output_quantity": 21,
        "inputs": [{"item_id": arroz["id"], "quantity": 2}],
    }).json()
    assert p["deviation_percent"] == pytest.approx(5.0)
    assert p["unit_cost"] == pytest.approx(12 / 21, rel=1e-3)


def test_venda_baixa_porcoes_e_embalagem_nao_o_cru():
    coxao, emb, bife, estrog = montar_coxao()
    client.post("/api/stock/purchase", json={"item_id": coxao["id"], "quantity": 10, "total_price": 360})
    client.post("/api/stock/purchase", json={"item_id": emb["id"], "quantity": 100, "total_price": 90})
    client.post("/api/production", json={"item_id": bife["id"], "output_quantity": 30,
                                         "inputs": [{"item_id": coxao["id"], "quantity": 5}]})
    r = client.post("/api/sales", json={"lines": [{"item_id": estrog["id"], "quantity": 4}]})
    assert r.status_code == 201, r.text
    assert r.json()["total"] == 160
    assert get(bife["id"])["stock"] == pytest.approx(26)
    assert get(emb["id"])["stock"] == pytest.approx(96)
    assert get(coxao["id"])["stock"] == pytest.approx(5)  # cru não mexe na venda


def test_desfazer_venda_devolve_estoque():
    coxao, emb, bife, estrog = montar_coxao()
    client.post("/api/production", json={"item_id": bife["id"], "output_quantity": 12,
                                         "inputs": [{"item_id": coxao["id"], "quantity": 2}]})
    client.post("/api/sales", json={"lines": [{"item_id": estrog["id"], "quantity": 3}]})
    sale_id = client.get("/api/sales").json()[0]["id"]
    assert client.delete(f"/api/sales/{sale_id}").status_code == 204
    assert get(bife["id"])["stock"] == pytest.approx(12)


def test_custo_da_ficha_em_cadeia_peito_bife_file():
    peito = item(name="Peito de frango", kind="compra", unit="kg", avg_cost=20)
    bife = item(name="Bife de frango", kind="producao", unit="un", yield_quantity=8,
                recipe=[{"component_id": peito["id"], "quantity": 1}])
    tiras = item(name="Tiras de frango", kind="producao", unit="kg", yield_quantity=1,
                 recipe=[{"component_id": bife["id"], "quantity": 8}])
    prato = item(name="Estrogonofe de frango", kind="venda", selling_price=30,
                 recipe=[{"component_id": tiras["id"], "quantity": 0.15}])
    assert get(bife["id"])["unit_cost"] == pytest.approx(2.5)
    assert get(tiras["id"])["unit_cost"] == pytest.approx(20)
    p = get(prato["id"])
    assert p["unit_cost"] == pytest.approx(3.0)
    assert p["cmv_percent"] == pytest.approx(10.0)


def test_ficha_circular_e_prato_como_componente_sao_bloqueados():
    a = item(name="A", kind="producao", unit="kg", yield_quantity=1)
    b = item(name="B", kind="producao", unit="kg", yield_quantity=1,
             recipe=[{"component_id": a["id"], "quantity": 1}])
    r = client.put(f"/api/items/{a['id']}", json={"name": "A", "kind": "producao", "unit": "kg",
                                                  "yield_quantity": 1,
                                                  "recipe": [{"component_id": b["id"], "quantity": 1}]})
    assert r.status_code == 400
    prato = item(name="Prato", kind="venda", recipe=[{"component_id": a["id"], "quantity": 1}])
    r = client.post("/api/items", json={"name": "C", "kind": "producao", "unit": "kg",
                                        "recipe": [{"component_id": prato["id"], "quantity": 1}]})
    assert r.status_code == 400


def test_reposicao_desce_pela_cadeia_e_arredonda_pacote():
    batata = item(name="Batata palito", kind="compra", unit="kg", pack_size=2, pack_label="pacote")
    porcao = item(name="Batata porção 200g", kind="producao", unit="un", yield_quantity=10,
                  coverage_days=3, recipe=[{"component_id": batata["id"], "quantity": 2}])
    frita = item(name="Batata frita", kind="venda", selling_price=15,
                 recipe=[{"component_id": porcao["id"], "quantity": 1}])
    client.post("/api/stock/purchase", json={"item_id": batata["id"], "quantity": 2, "total_price": 22})
    client.post("/api/production", json={"item_id": porcao["id"], "output_quantity": 10,
                                         "inputs": [{"item_id": batata["id"], "quantity": 2}]})
    # vende 8 porções: sobra 2
    client.post("/api/sales", json={"lines": [{"item_id": frita["id"], "quantity": 8}]})
    rep = client.get("/api/reports/replenishment").json()
    prod = {r["name"]: r for r in rep["produce"]}
    buy = {r["name"]: r for r in rep["buy"]}
    assert "Batata porção 200g" in prod
    p = prod["Batata porção 200g"]
    assert p["suggested"] == pytest.approx(p["target"] - 2, abs=1)
    assert p["suggested"] == int(p["suggested"])
    # a produção sugerida consome batata que não tem → compra em pacotes de 2 kg
    b = buy["Batata palito"]
    assert b["for_production"] > 0
    assert b["suggested"] % 2 == 0
    assert b["packs"] == b["suggested"] / 2


def test_lote_minimo_nhoque():
    farinha = item(name="Farinha", kind="compra", unit="kg", avg_cost=5)
    nhoque = item(name="Nhoque porção", kind="producao", unit="un", yield_quantity=8,
                  min_batch=16, coverage_days=12,
                  recipe=[{"component_id": farinha["id"], "quantity": 1}])
    prato = item(name="Nhoque ao sugo", kind="venda",
                 recipe=[{"component_id": nhoque["id"], "quantity": 1}])
    client.post("/api/production", json={"item_id": nhoque["id"], "output_quantity": 2,
                                         "inputs": [{"item_id": farinha["id"], "quantity": 0.25}]})
    client.post("/api/sales", json={"lines": [{"item_id": prato["id"], "quantity": 1}]})
    rep = client.get("/api/reports/replenishment").json()
    n = next(r for r in rep["produce"] if r["name"] == "Nhoque porção")
    assert n["suggested"] >= 16


def test_versao_exposta():
    from app.version import __version__
    assert client.get("/api/version").json() == {"version": __version__}


def test_ficha_em_gramas_para_item_em_kg():
    macarrao = item(name="Macarrão espaguete", kind="compra", unit="kg",
                    pack_size=0.5, pack_label="pacote", avg_cost=11.8)
    prato = item(name="Espaguete", kind="venda", selling_price=30,
                 recipe=[{"component_id": macarrao["id"], "quantity": 300, "unit": "g"}])
    assert prato["recipe"][0]["quantity"] == pytest.approx(0.3)
    assert prato["unit_cost"] == pytest.approx(3.54)
    r = client.post("/api/items", json={"name": "Errado", "kind": "venda",
                                        "recipe": [{"component_id": macarrao["id"], "quantity": 1, "unit": "L"}]})
    assert r.status_code == 400


def test_compra_em_gramas_e_em_pacotes():
    macarrao = item(name="Macarrão", kind="compra", unit="kg", pack_size=0.5)
    # 10 pacotes de 500 g a R$ 5,90 cada = 5 kg por R$ 59 → R$ 11,80/kg
    r = client.post("/api/stock/purchase", json={"item_id": macarrao["id"], "quantity": 5000,
                                                 "unit": "g", "total_price": 59})
    assert r.status_code == 200, r.text
    m = get(macarrao["id"])
    assert m["stock"] == pytest.approx(5)
    assert m["avg_cost"] == pytest.approx(11.8)


def test_ficha_lembra_unidade_digitada():
    tomate = item(name="Tomate", kind="compra", unit="kg", avg_cost=10.9)
    base = item(name="Base molho", kind="producao", unit="g", yield_quantity=3000,
                recipe=[{"component_id": tomate["id"], "quantity": 1500, "unit": "g"}])
    linha = base["recipe"][0]
    assert linha["quantity"] == pytest.approx(1.5)          # gravado em kg
    assert (linha["display_quantity"], linha["display_unit"]) == (1500, "g")  # exibido como digitado
    assert base["unit_cost"] == pytest.approx(16.35 / 3000, rel=1e-4)  # custo por g com precisão
    detalhe = client.get(f"/api/items/{base['id']}/cost").json()["lines"][0]
    assert (detalhe["display_quantity"], detalhe["display_unit"]) == (1500, "g")


def test_banco_antigo_sem_coluna_unit_e_migrado(tmp_path):
    import sqlite3
    from sqlalchemy import create_engine
    import app.database as database
    db_file = tmp_path / "antigo.db"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE recipe_lines (id INTEGER PRIMARY KEY, parent_id INTEGER, component_id INTEGER, quantity FLOAT, position INTEGER)")
    con.commit(); con.close()
    original = database.engine
    database.engine = create_engine(f"sqlite:///{db_file}")
    try:
        database.init_db()
    finally:
        database.engine.dispose(); database.engine = original
    cols = [r[1] for r in sqlite3.connect(db_file).execute("PRAGMA table_info(recipe_lines)")]
    assert "unit" in cols


def test_porcao_com_peso_rendimento_em_kg():
    macarrao = item(name="Macarrão", kind="compra", unit="kg", avg_cost=11.8)
    porcao = item(name="Porção espaguete", kind="producao", unit="un",
                  portion_size=300, portion_unit="g", yield_quantity=3, yield_unit="kg",
                  recipe=[{"component_id": macarrao["id"], "quantity": 1500, "unit": "g"}])
    assert porcao["yield_quantity"] == pytest.approx(10)          # 3 kg ÷ 300 g
    assert (porcao["yield_display"], porcao["yield_unit"]) == (3, "kg")
    assert porcao["unit_cost"] == pytest.approx(1.77)              # 17,70 ÷ 10
    assert "g" in porcao["units"] and "un" in porcao["units"]
    # prato usando 150 g da porção = meia porção
    prato = item(name="Espaguete kids", kind="venda", selling_price=20,
                 recipe=[{"component_id": porcao["id"], "quantity": 150, "unit": "g"}])
    assert prato["recipe"][0]["quantity"] == pytest.approx(0.5)
    assert (prato["recipe"][0]["display_quantity"], prato["recipe"][0]["display_unit"]) == (150, "g")
    # produção pesada em kg: 1,5 kg cru rendeu 3,3 kg cozido = 11 porções
    client.post("/api/stock/purchase", json={"item_id": macarrao["id"], "quantity": 5, "total_price": 59})
    p = client.post("/api/production", json={"item_id": porcao["id"], "output_quantity": 3.3, "output_unit": "kg",
                                             "inputs": [{"item_id": macarrao["id"], "quantity": 1.5}]}).json()
    assert p["output_quantity"] == pytest.approx(11)
    assert p["deviation_percent"] == pytest.approx(10.0)
    # sem peso da porção, rendimento em kg é recusado
    r = client.post("/api/items", json={"name": "Sem peso", "kind": "producao", "unit": "un",
                                        "yield_quantity": 3, "yield_unit": "kg"})
    assert r.status_code == 400


def test_perda_no_preparo_custo_e_baixa_pelo_bruto():
    cebola = item(name="Cebola", kind="compra", unit="kg", avg_cost=9.0, loss_percent=10)
    peito = item(name="Peito congelado", kind="compra", unit="kg", avg_cost=18.0, loss_percent=20)
    molho = item(name="Molho", kind="producao", unit="g", yield_quantity=1000, recipe=[
        {"component_id": cebola["id"], "quantity": 450, "unit": "g"},                     # usa 10% do item
        {"component_id": peito["id"], "quantity": 400, "unit": "g", "loss_percent": 25},   # sobrescreve na receita
    ])
    l_ceb, l_pei = molho["recipe"]
    assert l_ceb["effective_loss"] == 10 and l_ceb["loss_percent"] is None
    assert l_ceb["gross_quantity"] == pytest.approx(0.5)            # 450 g limpos ÷ 0,9 = 500 g brutos
    assert l_pei["gross_quantity"] == pytest.approx(0.4 / 0.75)
    assert (l_ceb["display_quantity"], l_ceb["display_unit"]) == (450, "g")
    custo = 0.5 * 9.0 + (0.4 / 0.75) * 18.0
    assert molho["unit_cost"] == pytest.approx(custo / 1000, rel=1e-4)
    # prato com 300 g limpos de peito: a venda baixa o bruto (300 ÷ 0,8 = 375 g)
    prato = item(name="Frango grelhado", kind="venda", selling_price=30,
                 recipe=[{"component_id": peito["id"], "quantity": 300, "unit": "g"}])
    client.post("/api/stock/purchase", json={"item_id": peito["id"], "quantity": 10, "total_price": 180})
    client.post("/api/sales", json={"lines": [{"item_id": prato["id"], "quantity": 2}]})
    assert get(peito["id"])["stock"] == pytest.approx(10 - 2 * 0.375)
    assert get(prato["id"])["unit_cost"] == pytest.approx(0.375 * 18.0)
    # mudar a perda padrão do item atualiza as fichas que usam o padrão
    client.put(f"/api/items/{cebola['id']}", json={"name": "Cebola", "kind": "compra", "unit": "kg", "loss_percent": 0})
    assert get(molho["id"])["recipe"][0]["gross_quantity"] == pytest.approx(0.45)
