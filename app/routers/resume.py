from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResumeModule
from app.constants import DEFAULT_RESUME_CATEGORIES, merge_options
from app.templating import templates

router = APIRouter()


def _category_options(db: Session) -> list[str]:
    values = [row[0] for row in db.query(ResumeModule.category).distinct()]
    return merge_options(DEFAULT_RESUME_CATEGORIES, values)


def _modules_by_category(db: Session, category: str) -> list[ResumeModule]:
    return (
        db.query(ResumeModule)
        .filter(ResumeModule.category == category)
        .order_by(ResumeModule.sort_order, ResumeModule.id)
        .all()
    )


def _render_panel(request: Request, db: Session, category: str):
    return templates.TemplateResponse(
        "resume/_panel.html",
        {
            "request": request,
            "selected_category": category,
            "modules": _modules_by_category(db, category),
        },
    )


@router.get("/resume", response_class=HTMLResponse)
def resume_home(request: Request, category: str | None = None, db: Session = Depends(get_db)):
    categories = _category_options(db)
    selected = category or (categories[0] if categories else None)
    return templates.TemplateResponse(
        "resume/index.html",
        {
            "request": request,
            "categories": categories,
            "selected_category": selected,
            "modules": _modules_by_category(db, selected) if selected else [],
            "active_nav": "resume",
        },
    )


@router.get("/resume/categories/{category}", response_class=HTMLResponse)
def resume_category_panel(request: Request, category: str, db: Session = Depends(get_db)):
    return _render_panel(request, db, category)


@router.post("/resume/modules", response_class=HTMLResponse)
def create_module(
    request: Request,
    category: str = Form(...),
    title: str = Form(""),
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    category = category.strip()
    existing_count = db.query(ResumeModule).filter(ResumeModule.category == category).count()
    module = ResumeModule(category=category, title=title.strip() or None, content=content, sort_order=existing_count)
    db.add(module)
    db.commit()
    return _render_panel(request, db, category)


@router.get("/resume/modules/{module_id}/edit", response_class=HTMLResponse)
def edit_module_form(request: Request, module_id: int, db: Session = Depends(get_db)):
    module = db.get(ResumeModule, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return templates.TemplateResponse("resume/_module_edit_form.html", {"request": request, "module": module})


@router.put("/resume/modules/{module_id}", response_class=HTMLResponse)
def update_module(
    request: Request,
    module_id: int,
    title: str = Form(""),
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    module = db.get(ResumeModule, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    module.title = title.strip() or None
    module.content = content
    db.commit()
    return _render_panel(request, db, module.category)


@router.delete("/resume/modules/{module_id}", response_class=HTMLResponse)
def delete_module(request: Request, module_id: int, db: Session = Depends(get_db)):
    module = db.get(ResumeModule, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    category = module.category
    db.delete(module)
    db.commit()
    return _render_panel(request, db, category)


@router.post("/resume/modules/{module_id}/move", response_class=HTMLResponse)
def move_module(
    request: Request,
    module_id: int,
    direction: str = Form(...),
    db: Session = Depends(get_db),
):
    module = db.get(ResumeModule, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    siblings = _modules_by_category(db, module.category)
    index = siblings.index(module)
    swap_index = index - 1 if direction == "up" else index + 1
    if 0 <= swap_index < len(siblings):
        neighbor = siblings[swap_index]
        module.sort_order, neighbor.sort_order = neighbor.sort_order, module.sort_order
        db.commit()
    return _render_panel(request, db, module.category)
