from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import Base, engine
from app import models  # noqa: F401
from app.routers import companies


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MyOffer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(companies.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.headers.get("HX-Request"):
        message = exc.errors()[0]["msg"]
        return HTMLResponse(content=f"<div class='error'>表单校验失败：{message}</div>", status_code=422)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health():
    return {"status": "ok"}
