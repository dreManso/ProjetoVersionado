import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Pode ser trocado por variável de ambiente (usado nos testes)
SQLALCHEMY_DATABASE_URL = os.environ.get("COZINHA_DB", "sqlite:///./cozinha.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Cria as tabelas e aplica ajustes em bancos de versões anteriores."""
    from . import models  # noqa: F401  (registra as tabelas)
    Base.metadata.create_all(bind=engine)
    new_columns = [
        ("recipe_lines", "unit", "VARCHAR(5)"),   # 2.3.1: unidade digitada em cada linha da ficha
        ("items", "yield_unit", "VARCHAR(5)"),    # 2.4.0: rendimento digitado em kg/g
        ("items", "portion_size", "FLOAT"),       # 2.4.0: peso da porção
        ("items", "portion_unit", "VARCHAR(5)"),
    ]
    with engine.begin() as conn:
        for table, column, sqltype in new_columns:
            cols = [r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})")]
            if column not in cols:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {sqltype}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
