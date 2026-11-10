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
    with engine.begin() as conn:
        cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(recipe_lines)")]
        if "unit" not in cols:  # 2.3.1: unidade digitada em cada linha da ficha
            conn.exec_driver_sql("ALTER TABLE recipe_lines ADD COLUMN unit VARCHAR(5)")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
