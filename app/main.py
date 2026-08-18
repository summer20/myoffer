from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import LoginRequiredMiddleware
from app.config import SECRET_KEY
from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401
from app.paths import resource_path
from app.routers import auth, companies, applications, resume
from app.seed_data import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="MyOffer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")
# Order matters: SessionMiddleware must run first so `request.session` exists
# by the time LoginRequiredMiddleware inspects it. Starlette runs middleware
# in the reverse of the order added, so SessionMiddleware is added last.
app.add_middleware(LoginRequiredMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(applications.router)
app.include_router(resume.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.headers.get("HX-Request"):
        message = exc.errors()[0]["msg"]
        return HTMLResponse(content=f"<div class='error'>表单校验失败：{message}</div>", status_code=422)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.headers.get("HX-Request"):
        return HTMLResponse(content=f"<div class='error'>{exc.detail}</div>", status_code=exc.status_code)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
def health():
    return {"status": "ok"}
