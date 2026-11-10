"""
Modelo único de "Item" com três tipos:

  compra    → insumo comprado (coxão mole em peça, arroz cru, batata em pacote,
              embalagem, lacre, saco de entrega...). Tem estoque e custo médio.
  producao  → subproduto feito na cozinha (bife 129 g, porção de arroz 250 g,
              nhoque congelado, porção de batata 200 g, frango desfiado...).
              Tem ficha técnica (o que entra em UMA receita/lote), rendimento
              e estoque próprio.
  venda     → prato do cardápio. Tem ficha técnica (o que vai em 1 prato) e
              preço. Não tem estoque: é montado na hora com as porções.

Toda quantidade de ficha técnica está na unidade do componente.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base

KINDS = ("compra", "producao", "venda")
UNITS = ("kg", "g", "L", "mL", "un")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    kind = Column(String(10), nullable=False)
    unit = Column(String(5), nullable=False, default="un")
    stock = Column(Float, nullable=False, default=0.0)
    min_stock = Column(Float, nullable=False, default=0.0)        # estoque de segurança
    coverage_days = Column(Float, nullable=False, default=6.0)    # dias de trabalho a cobrir
    avg_cost = Column(Float, nullable=False, default=0.0)         # custo médio real por unidade
    yield_quantity = Column(Float, nullable=True)                 # producao: rende por receita (na unidade de estoque)
    yield_unit = Column(String(5), nullable=True)                 # unidade em que o rendimento foi digitado (exibição)
    portion_size = Column(Float, nullable=True)                   # producao em "un": peso/volume de cada porção
    portion_unit = Column(String(5), nullable=True)               # g, kg, mL ou L
    min_batch = Column(Float, nullable=False, default=0.0)        # producao: lote mínimo
    loss_percent = Column(Float, nullable=False, default=0.0)     # perda no preparo (casca, descongelamento...)
    pack_size = Column(Float, nullable=True)                      # compra: tamanho da embalagem
    pack_label = Column(String(30), nullable=True)                # compra: "pacote", "caixa"...
    selling_price = Column(Float, nullable=True)                  # venda
    notes = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    recipe = relationship(
        "RecipeLine",
        foreign_keys="RecipeLine.parent_id",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="RecipeLine.position",
    )


class RecipeLine(Base):
    __tablename__ = "recipe_lines"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)  # sempre na unidade de estoque do componente
    unit = Column(String(5), nullable=True)   # unidade em que foi digitada (só para exibir: 1500 g)
    loss_percent = Column(Float, nullable=True)  # perda nesta receita; vazio = perda padrão do item
    position = Column(Integer, nullable=False, default=0)

    parent = relationship("Item", foreign_keys=[parent_id], back_populates="recipe")
    component = relationship("Item", foreign_keys=[component_id])

    @property
    def effective_loss(self) -> float:
        v = self.loss_percent if self.loss_percent is not None else (self.component.loss_percent or 0.0)
        return min(max(v or 0.0, 0.0), 95.0)

    @property
    def gross_quantity(self) -> float:
        """Quantidade bruta que sai do estoque: líquida ÷ (1 − perda). Ex.: 500 g limpos, 10% casca → 555,6 g."""
        return self.quantity / (1 - self.effective_loss / 100)


class Production(Base):
    __tablename__ = "productions"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    output_quantity = Column(Float, nullable=False)     # rendimento real
    expected_output = Column(Float, nullable=True)      # rendimento pela ficha
    input_cost = Column(Float, nullable=False, default=0.0)
    date = Column(DateTime, nullable=False, default=datetime.now)
    notes = Column(String(255))

    item = relationship("Item")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.now)

    item = relationship("Item")


class Movement(Base):
    """Toda alteração de estoque. quantity > 0 entra, < 0 sai."""
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    # compra | producao_entrada | producao_consumo | venda | ajuste
    type = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=True)
    date = Column(DateTime, nullable=False, default=datetime.now, index=True)
    notes = Column(String(255))
    production_id = Column(Integer, ForeignKey("productions.id"), nullable=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)

    item = relationship("Item")
