# Histórico de versões

A versão aparece no menu do app, ao lado de "Cozinha".

## 2.9.0 — 10/11/2026
- Revenda sem cadastro duplo: no item comprado (refrigerante, água, cerveja...), marque "Também vendo direto ao cliente" e informe o preço. Não precisa criar um prato.
- O item aparece no fechamento de vendas e na aba "Pratos do cardápio" (marcado "venda direta"), com lucro, CMV e preço iFood.
- Cada venda tira do estoque do próprio item, e a média de vendas entra na lista de compras (arredondada para o fardo/caixa).
- Vale também para itens produzidos vendidos avulsos (ex.: porção de farofa).

## 2.8.0 — 10/11/2026
- Reposição calculada pelas VENDAS: a média de pratos vendidos por dia desce pelas fichas (prato → porções → insumos) e forma a lista de produção e a de compras.
- Produções, compras e contagens não entram mais na média (uma produção de teste não infla as compras).
- O que já está pronto em porções conta como estoque do insumo ("na cadeia"): feijão porcionado conta como feijão.
- Aviso quando não há vendas lançadas.

## 2.7.2 — 10/11/2026
- A perda (preparo ou defeito) agora aumenta só o CUSTO. A quantidade que sai do estoque, a da produção e a da lista de compras são as da ficha.
- Reposição: com menos de uma semana de lançamentos, a média de consumo é dividida por pelo menos 6 dias (antes, 1 dia de teste virava média de 1 dia e inflava as compras). A tela avisa quantos dias de histórico existem.
- Estoque sem sobras de arredondamento ("-0 g").

## 2.7.1 — 10/11/2026
- Abrir no celular: o Painel mostra o endereço e um QR code para abrir o app no celular (mesmo Wi-Fi). A janela preta também mostra o endereço ao iniciar.

## 2.7.0 — 10/11/2026
- Calculadora integrada em todos os campos de número:
  - dá para digitar a conta direto no campo (ex.: 4700+2000, 3*500, 21,60/24, 10%); o resultado aparece embaixo e entra no campo ao sair dele ou apertar Enter;
  - botão de calculadora ao lado do campo, com teclado (+ − × ÷, parênteses, %) e botão "Usar".

## 2.6.0 — 10/11/2026
- Pratos: "Lucro sobre o custo %" ligado ao "Preço venda direta". Digite um e o outro é calculado.
- Preço iFood calculado automaticamente: venda direta ÷ (1 − taxa do iFood).
- Taxa do iFood única para todos os pratos (padrão 30%), editável na aba "Pratos do cardápio".
- Fechamento de vendas com canal "Venda direta" ou "iFood", usando o preço de cada canal.
- Lista de pratos mostra lucro, venda direta, iFood e CMV.

## 2.5.1 — 10/11/2026
- Campo renomeado para "Perda (preparo ou defeito)": serve também para unidades com defeito ou faltando no pacote (ex.: embalagens).
- Exemplo da perda usa a embalagem de compra: "1 pacote (24 un) → 23,04 un aproveitáveis".
- Quantidade bruta de itens em unidades mostrada com 2 casas (1,04 un em vez de 1 un).

## 2.5.0 — 10/11/2026
- Perda no preparo (fator de correção): cada item pode ter uma perda padrão (ex.: cebola 10% de casca, peito congelado 20% no descongelamento).
- Na ficha técnica, a quantidade é a LIMPA; o app calcula o bruto que sai do estoque e o custo real. Cada receita pode ter uma perda diferente para o item.
- Venda, produção e lista de reposição passam a usar o peso bruto.
- Itens comprados mostram também o custo por kg aproveitável.

## 2.4.0 — 10/11/2026
- Itens produzidos em porções podem ter o peso de cada porção (ex.: 300 g).
- Rendimento da receita em porções ou em kg pronto: 3 kg de macarrão cozido = 10 porções de 300 g.
- Custo mostrado por porção e por kg pronto.
- Produção: "quanto rendeu" pode ser pesado em kg/g e o app converte em porções.
- Ficha de prato pode usar a porção em gramas (ex.: 150 g = meia porção).

## 2.3.1 — 10/11/2026
- Ficha técnica lembra a unidade digitada: 1500 g continua aparecendo como 1500 g ao reabrir.
- Itens controlados em g ou mL mostram o preço por kg ou L (R$ 11,31/kg em vez de R$ 0,01/g).
- Aviso na ficha quando uma linha passa de 100 kg ou 100 L (provável grama digitada como kg).
- Se o programa já estiver aberto em outra janela, ele não atualiza por cima: avisa para fechar as janelas e abrir de novo (evita misturar versões).

## 2.3.0 — 10/11/2026
- Preço por embalagem: informe o preço do pacote (ex.: R$ 5,90 o pacote de 500 g) e o app calcula o preço por kg sozinho.
- Embalagem pode ser cadastrada em g, kg, mL ou L (ex.: 500 g).
- Ficha técnica aceita g ou kg (mL ou L) em cada linha: 300 g de macarrão vira 0,3 kg automaticamente.
- Entrada de compra aceita quantidade em pacotes, g ou kg.

## 2.2.0 — 10/11/2026
- Atualização automática: ao abrir, o programa baixa e instala a versão nova, sem tocar nos seus dados.

## 2.1.1 — 10/11/2026
- Número da versão aparece no menu do app.
- Removido o botão "Colar lista de comprados" (descartado a pedido).

## 2.1.0 — 09/11/2026
- Importador dos cadastros da primeira versão (`importar_v1.py`).

## 2.0.1 — 09/11/2026
- Instalação corrigida para Python 3.15 no Windows.
- Atalho `Abrir Cozinha.bat`: abre o programa e o navegador com dois cliques.

## 2.0.0 — 09/11/2026
- Estoque em vários níveis: comprado → produzido (porções, subprodutos) → prato.
- Venda baixa só as porções e embalagens do prato.
- Produção com rendimento real, perdas/ganhos no custo e alerta de desvio.
- Compra com peso bruto e valor total (custo médio). Contagem de estoque.
- Lista de reposição: produzir e comprar, com média de 4 semanas (6 dias/semana).
- Fechamento de vendas do dia.

## 1.0.0 — 17/06/2026
- Primeira versão: ingredientes, preparações, custo, vendas e estoque.
