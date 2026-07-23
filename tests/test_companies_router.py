from app.models import Company


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


def test_delete_company_with_applications_requires_confirm_then_cascades(client, db_engine):
    """Test that deleting a company with applications requires confirm=true,
    shows a confirmation prompt, and cascade-deletes both the company and its applications."""
    from sqlalchemy.orm import sessionmaker
    from app.models import Application

    # 1. Create a company via HTTP
    response = client.post(
        "/companies", data={"name": "快手", "industry": "互联网"}
    )
    assert response.status_code == 200

    # 2. Create an Application directly via ORM (since the POST endpoint doesn't exist yet)
    Session = sessionmaker(bind=db_engine)
    db = Session()
    try:
        app = Application(
            company_id=1, position="后端开发", base_city="北京", stage="已投递"
        )
        db.add(app)
        db.commit()
    finally:
        db.close()

    # 3. Call DELETE without confirm - should show confirmation prompt
    response = client.delete("/companies/1")
    assert response.status_code == 200
    assert "该公司下还有" in response.text
    assert "确认删除" in response.text

    # Verify both Company and Application still exist
    db = Session()
    try:
        company = db.query(Company).filter_by(id=1).first()
        application = db.query(Application).filter_by(id=1).first()
        assert company is not None, "Company should still exist after delete without confirm"
        assert application is not None, "Application should still exist after delete without confirm"
    finally:
        db.close()

    # 4. Call DELETE with confirm=true - should cascade-delete
    response = client.delete("/companies/1?confirm=true")
    assert response.status_code == 200

    # Verify both Company and Application are now deleted
    db = Session()
    try:
        company = db.query(Company).filter_by(id=1).first()
        application = db.query(Application).filter_by(id=1).first()
        assert company is None, "Company should be deleted after confirm=true"
        assert application is None, "Application should be cascade-deleted after confirm=true"
    finally:
        db.close()
