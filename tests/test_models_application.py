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
