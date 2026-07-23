# MyOffer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, single-user FastAPI web app that tracks a company/招聘 library, per-company application progress, and a copy-paste resume module library.

**Architecture:** FastAPI + SQLAlchemy ORM backed by a single SQLite file (`myoffer.db`). Jinja2 server-rendered templates; HTMX handles all create/update/delete without full page reloads; Alpine.js is used only for the client-side "copy to clipboard" button. No npm/build step — HTMX and Alpine are vendored as static JS files.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.0, SQLite, Jinja2, HTMX 1.9, Alpine.js 3, pytest + httpx for testing.

## Global Constraints

- Single local user, no login/auth, no multi-tenancy — copied verbatim from spec's "使用范围".
- No npm/webpack/build tooling — copied verbatim from spec's "技术栈".
- "预设选项 + 自定义新增" pattern for industry/city/stage/resume-category fields: default list ∪ `SELECT DISTINCT` existing values, no separate dictionary tables, `.strip()` before persisting.
- Each ResumeModule has exactly one version — no multi-variant support in this scope.
- Seed data must NOT fabricate `recruiting_open` / `recruiting_url` — leave blank/false, to be filled in later via WebSearch or manually.
- Out of scope for this plan (per spec's "明确不做的事"): multi-user accounts, AI/OCR resume parsing, resume module version variants, cloud deployment, automatic scraping, application stage history/timeline.

---

## File Structure

```
MyOffer/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── constants.py
│   ├── templating.py
│   ├── seed_data.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── companies.py
│   │   ├── applications.py
│   │   └── resume.py
│   └── templates/
│       ├── base.html
│       ├── companies/
│       │   ├── index.html
│       │   ├── _rows.html
│       │   └── _row.html
│       ├── applications/
│       │   ├── index.html
│       │   ├── _row.html
│       │   └── _form.html
│       └── resume/
│           ├── index.html
│           ├── _panel.html
│           ├── _module_card.html
│           └── _module_edit_form.html
├── static/
│   ├── style.css
│   └── vendor/
│       ├── htmx.min.js
│       └── alpine.min.js
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_constants.py
│   ├── test_models_company.py
│   ├── test_models_application.py
│   ├── test_models_resume.py
│   ├── test_companies_router.py
│   ├── test_applications_router.py
│   ├── test_resume_router.py
│   └── test_seed_data.py
├── requirements.txt
└── README.md
```

---

### Task 1: Project scaffolding, database module, FastAPI skeleton

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/database.py`
- Create: `app/main.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_health.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `app.database.Base` (declarative base), `app.database.engine`, `app.database.SessionLocal`, `app.database.get_db()` (FastAPI dependency generator), `app.main.app` (FastAPI instance). Tests: `client` fixture (FastAPI `TestClient` with `get_db` overridden to an isolated in-memory SQLite engine) and `db_engine` fixture (the raw SQLAlchemy engine backing that override).

- [ ] **Step 1: Create the project skeleton and a venv**

```bash
cd /Users/huiying.h.chen/MyOffer
mkdir -p app/routers app/templates/companies app/templates/applications app/templates/resume static/vendor tests
touch app/__init__.py app/routers/__init__.py tests/__init__.py
python3 -m venv .venv
```

- [ ] **Step 2: Write `requirements.txt` and install**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.35
jinja2==3.1.4
python-multipart==0.0.12
pytest==8.3.3
httpx==0.27.2
```

Run: `.venv/bin/pip install -r requirements.txt`

- [ ] **Step 3: Write the failing test and its fixtures**

`tests/conftest.py`:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Deliberately NOT using `with TestClient(app) as c:` — entering the
    # context manager fires the app's real @app.on_event("startup"), which
    # calls Base.metadata.create_all()/seed against the PRODUCTION engine
    # (app.database.engine), not this test's in-memory one. Plain
    # construction skips startup/shutdown entirely, which is fine because
    # this fixture already creates tables on the test engine directly.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
```

`tests/test_health.py`:
```python
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run the test and confirm it fails**

Run: `.venv/bin/pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.database'` (or similar import error) — `app/database.py` and `app/main.py` don't exist yet.

- [ ] **Step 5: Implement `app/database.py` and `app/main.py`**

`app/database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./myoffer.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`app/main.py`:
```python
from fastapi import FastAPI
from app.database import Base, engine

app = FastAPI(title="MyOffer")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Run the test and confirm it passes**

Run: `.venv/bin/pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add requirements.txt app tests
git commit -m "chore: project scaffolding with FastAPI health check"
```

---

### Task 2: Constants and the "预设+自定义" option-merging helper

**Files:**
- Create: `app/constants.py`
- Test: `tests/test_constants.py`

**Interfaces:**
- Consumes: nothing
- Produces: `app.constants.DEFAULT_INDUSTRIES`, `DEFAULT_SCALE_TAGS`, `DEFAULT_POSITIONS`, `DEFAULT_CITIES`, `DEFAULT_STAGES`, `DEFAULT_RESUME_CATEGORIES` (all `list[str]`), and `app.constants.merge_options(defaults: list[str], existing_values: list[str]) -> list[str]`.

- [ ] **Step 1: Write the failing test**

`tests/test_constants.py`:
```python
from app.constants import merge_options, DEFAULT_INDUSTRIES


def test_merge_options_keeps_defaults_first_and_appends_new_sorted():
    result = merge_options(["互联网", "游戏"], ["互联网", "金融", "教育"])
    assert result == ["互联网", "游戏", "教育", "金融"]


def test_merge_options_strips_and_ignores_blank_values():
    result = merge_options(["互联网"], ["  ", "", "互联网", " 金融 "])
    assert result == ["互联网", "金融"]


def test_default_industries_is_nonempty():
    assert len(DEFAULT_INDUSTRIES) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_constants.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.constants'`

- [ ] **Step 3: Implement `app/constants.py`**

```python
DEFAULT_INDUSTRIES = ["互联网", "游戏", "金融", "消费", "制造", "其他"]
DEFAULT_SCALE_TAGS = ["上市", "世界500强", "中国500强", "独角兽"]
DEFAULT_POSITIONS = [
    "后端开发",
    "前端开发",
    "算法工程师",
    "产品经理",
    "数据分析",
    "测试开发",
    "运营",
]
DEFAULT_CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京"]
DEFAULT_STAGES = [
    "已投递",
    "笔试",
    "测评",
    "一面",
    "二面",
    "三面",
    "HR面",
    "offer",
    "已拒",
    "已弃",
]
DEFAULT_RESUME_CATEGORIES = [
    "基本信息",
    "教育经历",
    "实习经历",
    "项目经历",
    "技能特长",
    "荣誉奖项",
    "自我评价",
]


def merge_options(defaults: list[str], existing_values: list[str]) -> list[str]:
    """defaults (in order) followed by any extra existing DB values, sorted, deduped, blanks dropped."""
    seen = set(defaults)
    extra = sorted(
        {v.strip() for v in existing_values if v and v.strip() and v.strip() not in seen}
    )
    return list(defaults) + extra
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_constants.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/constants.py tests/test_constants.py
git commit -m "feat: default option lists and merge_options helper"
```

---

### Task 3: Company model

**Files:**
- Create: `app/models.py`
- Modify: `app/main.py` (import models so `Base.metadata` knows about the table before `create_all`)
- Test: `tests/test_models_company.py`

**Interfaces:**
- Consumes: `app.database.Base` (Task 1)
- Produces: `app.models.Company` with columns `id, name, industry, scale_tags (JSON list), recruiting_open (bool), recruiting_url (str|None), notes (str|None)` and relationship `applications` (added fully in Task 4, declared here as empty-safe).

- [ ] **Step 1: Write the failing test**

`tests/test_models_company.py`:
```python
from app.models import Company


def test_create_and_query_company(db_session):
    company = Company(
        name="字节跳动",
        industry="互联网",
        scale_tags=["独角兽"],
        recruiting_open=True,
        recruiting_url="https://jobs.bytedance.com",
    )
    db_session.add(company)
    db_session.commit()

    fetched = db_session.query(Company).filter_by(name="字节跳动").one()
    assert fetched.industry == "互联网"
    assert fetched.scale_tags == ["独角兽"]
    assert fetched.recruiting_open is True
    assert fetched.applications == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_models_company.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: Implement `app/models.py` (Company only for now) and wire it into `main.py`**

`app/models.py`:
```python
from sqlalchemy import Column, Integer, String, Boolean, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    industry = Column(String, nullable=False)
    scale_tags = Column(JSON, nullable=False, default=list)
    recruiting_open = Column(Boolean, nullable=False, default=False)
    recruiting_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    applications = relationship(
        "Application", back_populates="company", cascade="all, delete-orphan"
    )
```

`app/main.py` (full file, adds the model import):
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.database import Base, engine
from app import models  # noqa: F401  (registers models with Base.metadata)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MyOffer", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
```

Note: `Application` doesn't exist yet — the `relationship("Application", ...)` string reference is resolved lazily by SQLAlchemy at first use, so this is safe even though the class is defined in Task 4.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_models_company.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/main.py tests/test_models_company.py
git commit -m "feat: Company model"
```

---

### Task 4: Application model and cascade delete

**Files:**
- Modify: `app/models.py` (add `Application`)
- Test: `tests/test_models_application.py`

**Interfaces:**
- Consumes: `app.models.Company` (Task 3)
- Produces: `app.models.Application` with columns `id, company_id (FK), position, base_city, stage, applied_date (date|None), updated_at (datetime, auto), notes (str|None)` and relationship `company`.

- [ ] **Step 1: Write the failing test**

`tests/test_models_application.py`:
```python
from app.models import Company, Application


def test_cascade_delete_removes_applications(db_session):
    company = Company(name="腾讯", industry="互联网", scale_tags=[])
    db_session.add(company)
    db_session.commit()

    application = Application(
        company_id=company.id,
        position="后端开发",
        base_city="深圳",
        stage="已投递",
    )
    db_session.add(application)
    db_session.commit()

    assert db_session.query(Application).count() == 1

    db_session.delete(company)
    db_session.commit()

    assert db_session.query(Application).count() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_models_application.py -v`
Expected: FAIL with `ImportError: cannot import name 'Application' from 'app.models'`

- [ ] **Step 3: Add `Application` to `app/models.py`**

Full file:
```python
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    JSON,
    DateTime,
    Date,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    industry = Column(String, nullable=False)
    scale_tags = Column(JSON, nullable=False, default=list)
    recruiting_open = Column(Boolean, nullable=False, default=False)
    recruiting_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    applications = relationship(
        "Application", back_populates="company", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    position = Column(String, nullable=False)
    base_city = Column(String, nullable=False)
    stage = Column(String, nullable=False, default="已投递")
    applied_date = Column(Date, nullable=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    notes = Column(Text, nullable=True)

    company = relationship("Company", back_populates="applications")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_models_application.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models_application.py
git commit -m "feat: Application model with cascade delete from Company"
```

---

### Task 5: ResumeModule model

**Files:**
- Modify: `app/models.py` (add `ResumeModule`)
- Test: `tests/test_models_resume.py`

**Interfaces:**
- Consumes: `app.database.Base`
- Produces: `app.models.ResumeModule` with columns `id, category, title (str|None), content, sort_order (int, default 0)`.

- [ ] **Step 1: Write the failing test**

`tests/test_models_resume.py`:
```python
from app.models import ResumeModule


def test_default_sort_order_and_optional_title(db_session):
    module = ResumeModule(category="项目经历", content="内容A")
    db_session.add(module)
    db_session.commit()

    fetched = db_session.query(ResumeModule).filter_by(category="项目经历").one()
    assert fetched.sort_order == 0
    assert fetched.title is None
    assert fetched.content == "内容A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_models_resume.py -v`
Expected: FAIL with `ImportError: cannot import name 'ResumeModule' from 'app.models'`

- [ ] **Step 3: Add `ResumeModule` to `app/models.py`** (append this class to the existing file, below `Application`)

```python
class ResumeModule(Base):
    __tablename__ = "resume_modules"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_models_resume.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models_resume.py
git commit -m "feat: ResumeModule model"
```

---

### Task 6: Companies router, templates, and HTMX-driven list/create/update/delete

**Files:**
- Create: `app/templating.py`
- Create: `app/routers/companies.py`
- Create: `app/templates/base.html`
- Create: `app/templates/companies/index.html`
- Create: `app/templates/companies/_rows.html`
- Create: `app/templates/companies/_row.html`
- Create: `static/style.css`
- Modify: `app/main.py` (mount static, include router, add HTMX-aware validation error handler)
- Test: `tests/test_companies_router.py`

**Interfaces:**
- Consumes: `app.models.Company` (Task 3), `app.constants.DEFAULT_INDUSTRIES`/`DEFAULT_SCALE_TAGS`/`merge_options` (Task 2), `app.database.get_db` (Task 1)
- Produces: `app.routers.companies.router` (FastAPI `APIRouter`), `app.routers.companies._query_companies(db, industry, recruiting_open, applied) -> list[Company]` and `app.routers.companies._render_rows(request, companies, pending_confirm_id=None) -> TemplateResponse` — both reused by the Applications router in Task 7. Routes: `GET /`, `POST /companies`, `PUT /companies/{id}`, `DELETE /companies/{id}?confirm=`.

- [ ] **Step 1: Download vendored JS (no npm/build step)**

```bash
mkdir -p static/vendor
curl -sL https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js -o static/vendor/htmx.min.js
curl -sL https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js -o static/vendor/alpine.min.js
```

- [ ] **Step 2: Write the failing tests**

`tests/test_companies_router.py`:
```python
def test_list_companies_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "公司库" in response.text


def test_create_company_appears_in_list(client):
    response = client.post(
        "/companies",
        data={"name": "字节跳动", "industry": "互联网", "scale_tags": ["独角兽"]},
    )
    assert response.status_code == 200
    assert "字节跳动" in response.text

    listing = client.get("/")
    assert "字节跳动" in listing.text


def test_update_company(client):
    client.post("/companies", data={"name": "腾讯", "industry": "互联网"})
    response = client.put(
        "/companies/1",
        data={"name": "腾讯科技", "industry": "互联网", "recruiting_open": "true"},
    )
    assert response.status_code == 200
    assert "腾讯科技" in response.text


def test_delete_company_without_applications(client):
    client.post("/companies", data={"name": "百度", "industry": "互联网"})
    response = client.delete("/companies/1")
    assert response.status_code == 200
    assert "百度" not in response.text


def test_create_company_missing_name_returns_htmx_error_fragment(client):
    response = client.post(
        "/companies",
        data={"industry": "互联网"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 422
    assert "error" in response.text
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_companies_router.py -v`
Expected: FAIL — `GET /` returns 404 (no route registered yet)

- [ ] **Step 4: Implement `app/templating.py`**

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
```

- [ ] **Step 5: Implement `app/routers/companies.py`**

```python
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
```

- [ ] **Step 6: Write templates**

`app/templates/base.html`:
```html
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>MyOffer</title>
    <link rel="stylesheet" href="/static/style.css">
    <script src="/static/vendor/htmx.min.js"></script>
    <script src="/static/vendor/alpine.min.js" defer></script>
</head>
<body>
    <nav class="topnav">
        <a href="/">公司库</a>
        <a href="/applications">投递看板</a>
        <a href="/resume">简历模块库</a>
    </nav>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

`app/templates/companies/index.html`:
```html
{% extends "base.html" %}
{% block content %}
<h1>公司库</h1>

<form class="filters" hx-get="/" hx-target="body" hx-push-url="true">
    <select name="industry">
        <option value="">全部类型</option>
        {% for opt in industry_options %}
        <option value="{{ opt }}" {% if opt == selected_industry %}selected{% endif %}>{{ opt }}</option>
        {% endfor %}
    </select>
    <label><input type="checkbox" name="recruiting_open" value="true"> 仅看已开启27秋招</label>
    <select name="applied">
        <option value="">全部</option>
        <option value="yes">已投递</option>
        <option value="no">未投递</option>
    </select>
    <button type="submit">筛选</button>
</form>

<table id="company-table">
    <thead>
        <tr><th>公司</th><th>类型</th><th>规模</th><th>27秋招</th><th>投递</th><th>操作</th></tr>
    </thead>
    <tbody id="company-rows">
        {% include "companies/_rows.html" %}
    </tbody>
</table>

<h2>新增公司</h2>
<form hx-post="/companies" hx-target="#company-rows" hx-swap="innerHTML">
    <input type="text" name="name" placeholder="公司名" required>
    <input type="text" name="industry" placeholder="类型（如 互联网）" required list="industry-list">
    <datalist id="industry-list">
        {% for opt in industry_options %}<option value="{{ opt }}">{% endfor %}
    </datalist>
    {% for tag in scale_tag_options %}
    <label><input type="checkbox" name="scale_tags" value="{{ tag }}"> {{ tag }}</label>
    {% endfor %}
    <label><input type="checkbox" name="recruiting_open" value="true"> 已开启27秋招</label>
    <input type="url" name="recruiting_url" placeholder="秋招链接">
    <button type="submit">新增</button>
</form>
{% endblock %}
```

`app/templates/companies/_rows.html`:
```html
{% for company in companies %}
{% include "companies/_row.html" %}
{% endfor %}
```

`app/templates/companies/_row.html`:
```html
<tr id="company-{{ company.id }}">
    <td>{{ company.name }}</td>
    <td>{{ company.industry }}</td>
    <td>{{ company.scale_tags | join(', ') }}</td>
    <td>
        {% if company.recruiting_open %}✅{% else %}—{% endif %}
        {% if company.recruiting_url %}<a href="{{ company.recruiting_url }}" target="_blank">链接</a>{% endif %}
    </td>
    <td>{% if company.applications %}已投递（{{ company.applications | length }}）{% else %}未投递{% endif %}</td>
    <td>
        {% if pending_confirm_id == company.id %}
            该公司下还有 {{ company.applications | length }} 条投递记录，确认一并删除？
            <button hx-delete="/companies/{{ company.id }}?confirm=true" hx-target="#company-rows" hx-swap="innerHTML">确认删除</button>
        {% else %}
            <button hx-get="/companies/{{ company.id }}/add-application-form" hx-target="#app-form-{{ company.id }}" hx-swap="innerHTML">+ 新增投递</button>
            <button hx-delete="/companies/{{ company.id }}" hx-target="#company-rows" hx-swap="innerHTML">删除</button>
        {% endif %}
    </td>
</tr>
<tr class="app-form-row"><td colspan="6"><div id="app-form-{{ company.id }}"></div></td></tr>
```

`static/style.css`:
```css
body { font-family: -apple-system, sans-serif; margin: 2rem; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }
.topnav a { margin-right: 1rem; }
.error { color: #b00020; }
.module-card { border: 1px solid #ccc; padding: 0.8rem; margin-bottom: 0.8rem; }
```

- [ ] **Step 7: Wire everything into `main.py`** (full file)

```python
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
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_companies_router.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 9: Commit**

```bash
git add app/templating.py app/routers/companies.py app/templates app/main.py static tests/test_companies_router.py
git commit -m "feat: companies list/create/update/delete with HTMX and cascade-delete confirmation"
```

---

### Task 7: Applications router, board page, and inline company-row form

**Files:**
- Create: `app/routers/applications.py`
- Create: `app/templates/applications/index.html`
- Create: `app/templates/applications/_row.html`
- Create: `app/templates/applications/_form.html`
- Modify: `app/main.py` (include applications router)
- Test: `tests/test_applications_router.py`

**Interfaces:**
- Consumes: `app.models.Company`, `app.models.Application` (Tasks 3–4), `app.constants.DEFAULT_POSITIONS`/`DEFAULT_CITIES`/`DEFAULT_STAGES`/`merge_options` (Task 2), `app.routers.companies._query_companies`/`_render_rows` (Task 6)
- Produces: `app.routers.applications.router`. Routes: `GET /companies/{company_id}/add-application-form`, `POST /companies/{company_id}/applications`, `GET /applications`, `PATCH /applications/{id}/stage`, `DELETE /applications/{id}`.

- [ ] **Step 1: Write the failing tests**

`tests/test_applications_router.py`:
```python
def _create_company(client, name="字节跳动"):
    client.post("/companies", data={"name": name, "industry": "互联网"})
    return 1


def test_create_application_updates_company_row_count(client):
    company_id = _create_company(client)
    response = client.post(
        f"/companies/{company_id}/applications",
        data={"position": "后端开发", "base_city": "北京", "stage": "已投递"},
    )
    assert response.status_code == 200
    assert "已投递（1）" in response.text


def test_list_applications_shows_company_and_position(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/applications",
        data={"position": "后端开发", "base_city": "北京", "stage": "已投递"},
    )
    response = client.get("/applications")
    assert response.status_code == 200
    assert "字节跳动" in response.text
    assert "后端开发" in response.text


def test_update_application_stage(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/applications",
        data={"position": "后端开发", "base_city": "北京", "stage": "已投递"},
    )
    response = client.patch("/applications/1/stage", data={"stage": "一面"})
    assert response.status_code == 200
    assert "一面" in response.text


def test_delete_application(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/applications",
        data={"position": "后端开发", "base_city": "北京", "stage": "已投递"},
    )
    response = client.delete("/applications/1")
    assert response.status_code == 200
    assert response.text.strip() == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_applications_router.py -v`
Expected: FAIL — `POST /companies/1/applications` returns 404 (route not registered)

- [ ] **Step 3: Implement `app/routers/applications.py`**

```python
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
```

- [ ] **Step 4: Write templates**

`app/templates/applications/_form.html`:
```html
<form hx-post="/companies/{{ company.id }}/applications" hx-target="#company-rows" hx-swap="innerHTML">
    <input type="text" name="position" placeholder="岗位" required list="position-list-{{ company.id }}">
    <datalist id="position-list-{{ company.id }}">
        {% for opt in position_options %}<option value="{{ opt }}">{% endfor %}
    </datalist>
    <input type="text" name="base_city" placeholder="base城市" required list="city-list-{{ company.id }}">
    <datalist id="city-list-{{ company.id }}">
        {% for opt in city_options %}<option value="{{ opt }}">{% endfor %}
    </datalist>
    <select name="stage">
        {% for opt in stage_options %}<option value="{{ opt }}">{{ opt }}</option>{% endfor %}
    </select>
    <input type="date" name="applied_date">
    <button type="submit">提交投递</button>
</form>
```

`app/templates/applications/_row.html`:
```html
<tr id="application-{{ application.id }}">
    <td>{{ application.company.name }}</td>
    <td>{{ application.position }}</td>
    <td>{{ application.base_city }}</td>
    <td>
        <form hx-patch="/applications/{{ application.id }}/stage" hx-target="#application-{{ application.id }}" hx-swap="outerHTML" hx-trigger="change">
            <select name="stage">
                {% for opt in stage_options %}
                <option value="{{ opt }}" {% if opt == application.stage %}selected{% endif %}>{{ opt }}</option>
                {% endfor %}
            </select>
        </form>
    </td>
    <td>{{ application.updated_at.strftime("%Y-%m-%d %H:%M") }}</td>
    <td>{{ application.notes or "" }}</td>
    <td><button hx-delete="/applications/{{ application.id }}" hx-target="#application-{{ application.id }}" hx-swap="outerHTML" hx-confirm="确认删除该投递记录？">删除</button></td>
</tr>
```

`app/templates/applications/index.html`:
```html
{% extends "base.html" %}
{% block content %}
<h1>我的投递看板</h1>

<form hx-get="/applications" hx-target="body" hx-push-url="true">
    <select name="stage">
        <option value="">全部阶段</option>
        {% for opt in stage_options %}
        <option value="{{ opt }}" {% if opt == selected_stage %}selected{% endif %}>{{ opt }}</option>
        {% endfor %}
    </select>
    <button type="submit">筛选</button>
</form>

<table id="application-table">
    <thead>
        <tr><th>公司</th><th>岗位</th><th>base</th><th>阶段</th><th>更新时间</th><th>备注</th><th>操作</th></tr>
    </thead>
    <tbody id="application-rows">
        {% for application in applications %}
            {% include "applications/_row.html" %}
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: Wire the router into `main.py`** (add one import line and one include line to the file from Task 6)

```python
from app.routers import companies, applications
...
app.include_router(companies.router)
app.include_router(applications.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_applications_router.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 7: Commit**

```bash
git add app/routers/applications.py app/templates/applications app/main.py tests/test_applications_router.py
git commit -m "feat: application tracking board with inline stage updates"
```

---

### Task 8: Resume module router, templates, reordering, and copy-to-clipboard

**Files:**
- Create: `app/routers/resume.py`
- Create: `app/templates/resume/index.html`
- Create: `app/templates/resume/_panel.html`
- Create: `app/templates/resume/_module_card.html`
- Create: `app/templates/resume/_module_edit_form.html`
- Modify: `app/main.py` (include resume router)
- Test: `tests/test_resume_router.py`

**Interfaces:**
- Consumes: `app.models.ResumeModule` (Task 5), `app.constants.DEFAULT_RESUME_CATEGORIES`/`merge_options` (Task 2)
- Produces: `app.routers.resume.router`. Routes: `GET /resume`, `GET /resume/categories/{category}`, `POST /resume/modules`, `GET /resume/modules/{id}/edit`, `PUT /resume/modules/{id}`, `DELETE /resume/modules/{id}`, `POST /resume/modules/{id}/move`.

- [ ] **Step 1: Write the failing tests**

`tests/test_resume_router.py`:
```python
def test_create_and_list_module(client):
    response = client.post(
        "/resume/modules",
        data={"category": "项目经历", "title": "推荐系统项目", "content": "使用协同过滤..."},
    )
    assert response.status_code == 200
    assert "推荐系统项目" in response.text

    page = client.get("/resume?category=项目经历")
    assert "推荐系统项目" in page.text


def test_update_module(client):
    client.post("/resume/modules", data={"category": "项目经历", "content": "初版内容"})
    response = client.put("/resume/modules/1", data={"title": "改标题", "content": "新内容"})
    assert response.status_code == 200
    assert "改标题" in response.text
    assert "新内容" in response.text


def test_reorder_modules_moves_second_above_first(client):
    client.post("/resume/modules", data={"category": "项目经历", "content": "模块A"})
    client.post("/resume/modules", data={"category": "项目经历", "content": "模块B"})
    response = client.post("/resume/modules/2/move", data={"direction": "up"})
    assert response.status_code == 200
    assert response.text.index("模块B") < response.text.index("模块A")


def test_delete_module(client):
    client.post("/resume/modules", data={"category": "项目经历", "content": "待删除"})
    response = client.delete("/resume/modules/1")
    assert response.status_code == 200
    assert "待删除" not in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_resume_router.py -v`
Expected: FAIL — `POST /resume/modules` returns 404 (route not registered)

- [ ] **Step 3: Implement `app/routers/resume.py`**

```python
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
```

- [ ] **Step 4: Write templates**

`app/templates/resume/_module_card.html`:
```html
<div class="module-card" id="module-{{ module.id }}">
    <h3>{{ module.title or module.category }}</h3>
    <pre class="module-content">{{ module.content }}</pre>
    <button x-data @click='navigator.clipboard.writeText({{ module.content | tojson }})'>复制</button>
    <button hx-get="/resume/modules/{{ module.id }}/edit" hx-target="#module-{{ module.id }}" hx-swap="outerHTML">编辑</button>
    <button hx-post="/resume/modules/{{ module.id }}/move" hx-vals='{"direction": "up"}' hx-target="#resume-panel" hx-swap="innerHTML">上移</button>
    <button hx-post="/resume/modules/{{ module.id }}/move" hx-vals='{"direction": "down"}' hx-target="#resume-panel" hx-swap="innerHTML">下移</button>
    <button hx-delete="/resume/modules/{{ module.id }}" hx-target="#resume-panel" hx-swap="innerHTML" hx-confirm="确认删除该模块？">删除</button>
</div>
```

`app/templates/resume/_module_edit_form.html`:
```html
<div class="module-card" id="module-{{ module.id }}">
    <form hx-put="/resume/modules/{{ module.id }}" hx-target="#resume-panel" hx-swap="innerHTML">
        <input type="text" name="title" value="{{ module.title or '' }}" placeholder="模块标题（可选）">
        <textarea name="content" required>{{ module.content }}</textarea>
        <button type="submit">保存</button>
    </form>
</div>
```

`app/templates/resume/_panel.html`:
```html
<h2>{{ selected_category }}</h2>
<div class="module-cards">
    {% for module in modules %}
    {% include "resume/_module_card.html" %}
    {% endfor %}
</div>

<form hx-post="/resume/modules" hx-target="#resume-panel" hx-swap="innerHTML">
    <input type="hidden" name="category" value="{{ selected_category }}">
    <input type="text" name="title" placeholder="模块标题（可选）">
    <textarea name="content" placeholder="粘贴简历内容" required></textarea>
    <button type="submit">新增模块</button>
</form>
```

`app/templates/resume/index.html`:
```html
{% extends "base.html" %}
{% block content %}
<h1>简历模块库</h1>
<div class="resume-layout">
    <nav class="resume-categories">
        {% for cat in categories %}
        <button hx-get="/resume/categories/{{ cat }}" hx-target="#resume-panel" hx-swap="innerHTML">{{ cat }}</button>
        {% endfor %}
    </nav>
    <div id="resume-panel">
        {% include "resume/_panel.html" %}
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Wire the router into `main.py`** (add one import name and one include line)

```python
from app.routers import companies, applications, resume
...
app.include_router(companies.router)
app.include_router(applications.router)
app.include_router(resume.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_resume_router.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 7: Commit**

```bash
git add app/routers/resume.py app/templates/resume app/main.py tests/test_resume_router.py
git commit -m "feat: resume module library with reorder and copy-to-clipboard"
```

---

### Task 9: Seed data, startup wiring, and README

**Files:**
- Create: `app/seed_data.py`
- Modify: `app/main.py` (call `seed_if_empty` on startup)
- Create: `README.md`
- Test: `tests/test_seed_data.py`

**Interfaces:**
- Consumes: `app.models.Company` (Task 3), `app.database.SessionLocal`/`engine` (Task 1)
- Produces: `app.seed_data.seed_if_empty(db: Session) -> int` (number of companies inserted; `0` if the table already had rows).

- [ ] **Step 1: Write the failing test**

`tests/test_seed_data.py`:
```python
from app.models import Company
from app.seed_data import seed_if_empty


def test_seed_is_idempotent(db_session):
    first_count = seed_if_empty(db_session)
    assert first_count > 0
    assert db_session.query(Company).count() == first_count

    second_count = seed_if_empty(db_session)
    assert second_count == 0
    assert db_session.query(Company).count() == first_count


def test_seed_does_not_fabricate_recruiting_links(db_session):
    seed_if_empty(db_session)
    companies = db_session.query(Company).all()
    assert all(c.recruiting_open is False for c in companies)
    assert all(c.recruiting_url is None for c in companies)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_seed_data.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.seed_data'`

- [ ] **Step 3: Implement `app/seed_data.py`**

```python
from sqlalchemy.orm import Session

from app.models import Company

SEED_COMPANIES = [
    {"name": "字节跳动", "industry": "互联网", "scale_tags": ["独角兽"]},
    {"name": "腾讯", "industry": "互联网", "scale_tags": ["上市", "世界500强"]},
    {"name": "阿里巴巴", "industry": "互联网", "scale_tags": ["上市", "世界500强"]},
    {"name": "百度", "industry": "互联网", "scale_tags": ["上市"]},
    {"name": "美团", "industry": "互联网", "scale_tags": ["上市", "世界500强"]},
    {"name": "拼多多", "industry": "互联网", "scale_tags": ["上市"]},
    {"name": "网易", "industry": "游戏", "scale_tags": ["上市"]},
    {"name": "米哈游", "industry": "游戏", "scale_tags": ["独角兽"]},
    {"name": "中信证券", "industry": "金融", "scale_tags": ["上市"]},
    {"name": "招商银行", "industry": "金融", "scale_tags": ["上市", "世界500强"]},
    {"name": "华为", "industry": "制造", "scale_tags": ["世界500强"]},
]


def seed_if_empty(db: Session) -> int:
    """Insert the seed companies only if the companies table is currently empty.

    recruiting_open/recruiting_url are intentionally left at their defaults
    (False/None) — these are time-sensitive and must be verified (e.g. via
    web search) or filled in by hand rather than fabricated here.
    """
    if db.query(Company).count() > 0:
        return 0
    for entry in SEED_COMPANIES:
        db.add(Company(name=entry["name"], industry=entry["industry"], scale_tags=entry["scale_tags"]))
    db.commit()
    return len(SEED_COMPANIES)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_seed_data.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Wire seeding into `main.py` startup** (full file)

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401
from app.routers import companies, applications, resume
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
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(companies.router)
app.include_router(applications.router)
app.include_router(resume.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.headers.get("HX-Request"):
        message = exc.errors()[0]["msg"]
        return HTMLResponse(content=f"<div class='error'>表单校验失败：{message}</div>", status_code=422)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Run the full test suite**

Run: `.venv/bin/pytest -v`
Expected: PASS — every test from Tasks 1–9 (health, constants, 3 model tests, 3 router test files, seed data)

- [ ] **Step 7: Write `README.md`**

```markdown
# MyOffer

个人秋招投递信息汇总工具（本地运行，单用户）。

## 运行

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/uvicorn app.main:app --reload

浏览器打开 http://localhost:8000 。首次启动会自动建表并灌入一份常见大厂种子数据（不含秋招链接，需要自己核实/补充）。

## 测试

    .venv/bin/pytest -v

## 手动验收路径（每次发版前过一遍）

1. 首页能看到种子公司列表，按类型筛选可用
2. 新增一家公司，填写类型/规模标签/秋招链接，保存后出现在列表里
3. 在某公司行内点"+ 新增投递"，填岗位/base/阶段提交，该公司"投递"列计数增加
4. 打开"投递看板"，能看到刚才那条记录，行内下拉直接改阶段，保存后更新时间刷新
5. 删除一家有投递记录的公司，应先看到确认提示，确认后才真正删除
6. 打开"简历模块库"，新增一个模块（选分类、填标题、粘贴正文），保存后出现在对应分类下
7. 点"复制"按钮，能把正文复制到剪贴板（粘贴到别处验证）
8. 新增第二个同分类模块，点"上移"，顺序确实互换
9. 编辑一个模块的标题/正文，保存后立刻反映在卡片上
10. 删除一个模块，卡片消失
```

- [ ] **Step 8: Commit**

```bash
git add app/seed_data.py app/main.py README.md tests/test_seed_data.py
git commit -m "feat: seed data, startup wiring, and README"
```
