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
