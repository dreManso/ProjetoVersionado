from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from .database import engine, Base
from .routers import ingredients, dishes, sales, reports

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Gestão de Restaurante", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingredients.router, prefix="/api/ingredients", tags=["Ingredientes"])
app.include_router(dishes.router, prefix="/api/dishes", tags=["Preparações"])
app.include_router(sales.router, prefix="/api/sales", tags=["Vendas"])
app.include_router(reports.router, prefix="/api/reports", tags=["Relatórios"])


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/index.html")


FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
