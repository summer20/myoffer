from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company
from app.constants import DEFAULT_INDUSTRIES, DEFAULT_SCALE_TAGS, merge_options
from app.templating import templates

router = APIRouter()


def _industry_options(db: Session) -> list[str]:
    values = [row[0] for row in db.query(Company.industry).distinct()]
    return merge_options(DEFAULT_INDUSTRIES, values)


def _query_companies(
    db: Session,
    industry: str | None,
    recruiting_open: bool | None,
    applied: str | None,
) -> list[Company]:
    query = db.query(Company)
    if industry:
        query = query.filter(Company.industry == industry)
    if recruiting_open is not None:
        query = query.filter(Company.recruiting_open == recruiting_open)
    companies = query.order_by(Company.name).all()
    if applied == "yes":
        companies = [c for c in companies if len(c.applications) > 0]
    elif applied == "no":
        companies = [c for c in companies if len(c.applications) == 0]
    return companies


def _render_rows(request: Request, companies: list[Company], pending_confirm_id: int | None = None):
    return templates.TemplateResponse(
        "companies/_rows.html",
        {"request": request, "companies": companies, "pending_confirm_id": pending_confirm_id},
    )


@router.get("/", response_class=HTMLResponse)
def list_companies(
    request: Request,
    industry: str | None = None,
    recruiting_open: bool | None = None,
    applied: str | None = None,
    db: Session = Depends(get_db),
):
    companies = _query_companies(db, industry, recruiting_open, applied)
    return templates.TemplateResponse(
        "companies/index.html",
        {
            "request": request,
            "companies": companies,
            "pending_confirm_id": None,
            "industry_options": _industry_options(db),
            "scale_tag_options": DEFAULT_SCALE_TAGS,
            "selected_industry": industry,
        },
    )


@router.post("/companies", response_class=HTMLResponse)
def create_company(
    request: Request,
    name: str = Form(...),
    industry: str = Form(...),
    scale_tags: list[str] = Form([]),
    recruiting_open: bool = Form(False),
    recruiting_url: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    company = Company(
        name=name.strip(),
        industry=industry.strip(),
        scale_tags=scale_tags,
        recruiting_open=recruiting_open,
        recruiting_url=recruiting_url.strip() or None,
        notes=notes.strip() or None,
    )
    db.add(company)
    db.commit()
    return _render_rows(request, _query_companies(db, None, None, None))


@router.put("/companies/{company_id}", response_class=HTMLResponse)
def update_company(
    request: Request,
    company_id: int,
    name: str = Form(...),
    industry: str = Form(...),
    scale_tags: list[str] = Form([]),
    recruiting_open: bool = Form(False),
    recruiting_url: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.name = name.strip()
    company.industry = industry.strip()
    company.scale_tags = scale_tags
    company.recruiting_open = recruiting_open
    company.recruiting_url = recruiting_url.strip() or None
    company.notes = notes.strip() or None
    db.commit()
    return _render_rows(request, _query_companies(db, None, None, None))


@router.delete("/companies/{company_id}", response_class=HTMLResponse)
def delete_company(
    request: Request,
    company_id: int,
    confirm: bool = False,
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if len(company.applications) > 0 and not confirm:
        companies = _query_companies(db, None, None, None)
        return _render_rows(request, companies, pending_confirm_id=company_id)
    db.delete(company)
    db.commit()
    return _render_rows(request, _query_companies(db, None, None, None))
