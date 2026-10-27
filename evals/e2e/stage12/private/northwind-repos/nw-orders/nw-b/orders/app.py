"""FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import init_db
from .routes import router
from .product_routes import router as product_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    yield


app = FastAPI(title="nw-orders", lifespan=lifespan)
app.include_router(router)
app.include_router(product_router)


@app.get("/health")
def health():
    return {"status": "ok"}
