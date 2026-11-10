# Controle de Cozinha

App para controlar estoque em vários níveis, custo real dos pratos e listas de produção e compra de um restaurante.

## Como rodar

```bash
pip install -r requirements.txt
python seed.py      # opcional: carrega dados de EXEMPLO (preços fictícios)
python run.py       # abre em http://localhost:8000
```

Tudo roda no seu computador: as contas são feitas pelo próprio app e não gastam créditos de IA. O app funciona sem internet. O banco de dados é o arquivo `cozinha.db`. Para recomeçar do zero, apague esse arquivo.

## Atualização automática

Ao abrir o programa (`Abrir Cozinha.bat` ou `python run.py`), ele confere se há versão nova no GitHub. Se houver, baixa e instala sozinho, mostra o que mudou e abre já atualizado. Os dados (`cozinha.db`) nunca são alterados pela atualização. Sem internet, abre a versão instalada. A versão aparece no menu, ao lado de "Cozinha", e o histórico fica no `CHANGELOG.md`.

## Trazer os cadastros da primeira versão

Se você usou a primeira versão (telas "Ingredientes" e "Preparações", arquivo `restaurante.db`):

```bash
python importar_v1.py                         # se o restaurante.db está nesta pasta
python importar_v1.py C:\caminho\restaurante.db  # se está em outra pasta
```

Ingredientes viram itens comprados (com custo e saldo), preparações usadas dentro de outras viram itens produzidos e as demais viram pratos. Gramas/quilos e mL/litros são convertidos. O importador só roda com o `cozinha.db` vazio, não altera o `restaurante.db` e salva em `relatorio_importacao.txt` o que precisa ser conferido.

## Como o app enxerga a cozinha

Todo item é de um de três tipos:

| Tipo | Exemplos | Estoque |
|---|---|---|
| **Comprado** | coxão mole em peça, arroz cru, batata palito em pacote de 2 kg, embalagem, lacre, saco | sim |
| **Produzido** | bife de coxão 129 g, porção de arroz 250 g, tiras de frango, frango desfiado, nhoque congelado, porção de batata 200 g | sim |
| **Prato** | Estrogonofe, Parmegiana, Nhoque ao sugo, Batata frita grande | não (é montado na hora) |

E três movimentos mudam o estoque:

```
COMPRA ───────────► PRODUÇÃO / FRACIONAMENTO ───────────► VENDA
peso bruto e        o que entrou (peso bruto real) e       baixa as porções e
valor total pago    o que rendeu de fato (contado/pesado)  embalagens da ficha do prato

Coxão mole (peça) → Bife 129g ─┬→ Estrogonofe / Milanesa / Parmegiana
Peito de frango ─┬→ Bife de frango → Tiras → Estrogonofe de frango
                 └→ Frango desfiado → Risoto
Batata 2 kg → Porção 200 g → Batata frita P (1 porção) / G (2 porções)
```

- **A venda baixa um nível só:** vender um Estrogonofe tira 1 bife, 1 porção de arroz e 1 embalagem. O coxão mole cru só sai do estoque quando os bifes são produzidos.
- **Perdas e ganhos ficam no custo:** a limpeza do coxão, a água do frango e o cozimento do arroz aparecem na diferença entre o que entrou e o que rendeu. O app mostra o desvio em relação à ficha e avisa quando o rendimento fica 5% ou mais abaixo dela.
- **Revenda (refrigerante, água, cerveja):** é só o item comprado com a opção "Também vendo direto ao cliente" e o preço. Não precisa de prato: a venda tira do estoque do próprio item e entra na lista de compras.
- **Estoque negativo é um aviso:** significa que alguma produção ou compra não foi lançada.

## Telas

- **Vendas:** fechamento do dia com a lista de pratos (digite as quantidades) ou colando uma lista (`Estrogonofe;12`). Lançamentos errados podem ser desfeitos, e as porções voltam ao estoque.
- **Produção:** registra lotes com o rendimento real. Mostra as sugestões do dia.
- **Estoque:** entrada de compra (que atualiza o custo médio), contagem física e histórico de movimentações.
- **Reposição:** lista do que produzir e do que comprar, pronta para imprimir.
- **Itens e fichas:** cadastro, ficha técnica, custo detalhado e preço sugerido por CMV.

## Regra da reposição

- A demanda vem dos **pratos vendidos**: média das últimas **4 semanas** ÷ dias de trabalho (**6 dias por semana**; com menos de uma semana de vendas, divide por pelo menos 6 dias).
- Pelas fichas técnicas, a venda de pratos vira consumo diário de porções/subprodutos e, por eles, de insumos (prato → porção → insumo).
- Estoque na cadeia: o que já está pronto em porções conta como estoque do insumo.
- Alvo = consumo por dia × **dias de cobertura** do item + estoque de segurança. Falta = alvo − estoque na cadeia (e nunca menos do que a produção sugerida vai tirar do item).
- Os itens produzidos são calculados primeiro; a lista de compras sai arredondada para a embalagem do fornecedor.
- Para itens que dão muito trabalho para pouca diferença de tempo (nhoque, bifes), aumente os **dias de cobertura** (ex.: 12) e defina um **lote mínimo**.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```
