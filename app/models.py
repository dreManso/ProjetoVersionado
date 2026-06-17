from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False)
    cost_per_unit = Column(Float, nullable=False)
    stock_quantity = Column(Float, default=0.0)
    min_stock = Column(Float, default=0.0)

    components = relationship(
        "DishComponent",
        back_populates="ingredient",
        foreign_keys="DishComponent.ingredient_id"
    )
    stock_movements = relationship("StockMovement", back_populates="ingredient")


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    preparation_steps = Column(Text)
    # rendimento real da receita (informado após preparação)
    yield_quantity = Column(Float, nullable=True)
    yield_unit = Column(String(20), nullable=True)
    selling_price = Column(Float, nullable=True)
    is_sellable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # componentes que este prato usa
    components = relationship(
        "DishComponent",
        back_populates="dish",
        foreign_keys="DishComponent.dish_id",
        cascade="all, delete-orphan"
    )
    # onde este prato é usado como subproduto
    used_as_component = relationship(
        "DishComponent",
        back_populates="sub_dish",
        foreign_keys="DishComponent.sub_dish_id"
    )
    sales = relationship("Sale", back_populates="dish")


class DishComponent(Base):
    """
    Componente de um prato: pode ser um ingrediente bruto OU um subproduto (outro prato).
    Exatamente um dos dois (ingredient_id ou sub_dish_id) deve ser preenchido.
    """
    __tablename__ = "dish_components"

    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True)
    sub_dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)

    dish = relationship("Dish", back_populates="components", foreign_keys=[dish_id])
    ingredient = relationship("Ingredient", back_populates="components", foreign_keys=[ingredient_id])
    sub_dish = relationship("Dish", back_populates="used_as_component", foreign_keys=[sub_dish_id])


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity_sold = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

    dish = relationship("Dish", back_populates="sales")
    stock_movements = relationship("StockMovement", back_populates="sale")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    movement_type = Column(String(10), nullable=False)  # "in" | "out"
    quantity = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(255))
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)

    ingredient = relationship("Ingredient", back_populates="stock_movements")
    sale = relationship("Sale", back_populates="stock_movements")
