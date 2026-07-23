from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.database import Base, engine
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MyOffer", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
