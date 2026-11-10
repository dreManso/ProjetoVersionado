from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import items, production, reports, sales, stock
from .version import __version__

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Controle de Cozinha", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router, prefix="/api/items", tags=["Itens e fichas técnicas"])
app.include_router(stock.router, prefix="/api/stock", tags=["Estoque"])
app.include_router(production.router, prefix="/api/production", tags=["Produção"])
app.include_router(sales.router, prefix="/api/sales", tags=["Vendas"])
app.include_router(reports.router, prefix="/api/reports", tags=["Relatórios"])


@app.get("/api/version", tags=["Sistema"])
def version():
    return {"version": __version__}

# Frontend (montado por último para não capturar as rotas /api)
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
