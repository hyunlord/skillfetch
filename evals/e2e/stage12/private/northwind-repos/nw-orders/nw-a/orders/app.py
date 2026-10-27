"""FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import init_db
from .routes import router


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    yield


app = FastAPI(title="nw-orders", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
