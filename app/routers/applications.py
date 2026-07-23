from datetime import date, datetime

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Application
from app.constants import DEFAULT_POSITIONS, DEFAULT_CITIES, DEFAULT_STAGES, merge_options
from app.templating import templates
from app.routers.companies import _query_companies, _render_rows

router = APIRouter()


def _distinct_options(db: Session, column, defaults: list[str]) -> list[str]:
    values = [row[0] for row in db.query(column).distinct()]
    return merge_options(defaults, values)


@router.get("/companies/{company_id}/add-application-form", response_class=HTMLResponse)
def add_application_form(request: Request, company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return templates.TemplateResponse(
        "applications/_form.html",
        {
            "request": request,
            "company": company,
            "position_options": _distinct_options(db, Application.position, DEFAULT_POSITIONS),
            "city_options": _distinct_options(db, Application.base_city, DEFAULT_CITIES),
            "stage_options": DEFAULT_STAGES,
        },
    )


@router.post("/companies/{company_id}/applications", response_class=HTMLResponse)
def create_application(
    request: Request,
    company_id: int,
    position: str = Form(...),
    base_city: str = Form(...),
    stage: str = Form("已投递"),
    applied_date: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    application = Application(
        company_id=company_id,
        position=position.strip(),
        base_city=base_city.strip(),
        stage=stage.strip(),
        applied_date=date.fromisoformat(applied_date) if applied_date else None,
        notes=notes.strip() or None,
    )
    db.add(application)
    db.commit()
    return _render_rows(request, _query_companies(db, None, None, None))


@router.get("/applications", response_class=HTMLResponse)
def list_applications(request: Request, stage: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Application)
    if stage:
        query = query.filter(Application.stage == stage)
    applications = query.order_by(Application.updated_at.desc()).all()
    return templates.TemplateResponse(
        "applications/index.html",
        {
            "request": request,
            "applications": applications,
            "stage_options": DEFAULT_STAGES,
            "selected_stage": stage,
        },
    )


@router.patch("/applications/{application_id}/stage", response_class=HTMLResponse)
def update_application_stage(
    request: Request,
    application_id: int,
    stage: str = Form(...),
    db: Session = Depends(get_db),
):
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    application.stage = stage.strip()
    application.updated_at = datetime.utcnow()
    db.commit()
    return templates.TemplateResponse(
        "applications/_row.html",
        {"request": request, "application": application, "stage_options": DEFAULT_STAGES},
    )


@router.delete("/applications/{application_id}", response_class=HTMLResponse)
def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(application)
    db.commit()
    return HTMLResponse("")
