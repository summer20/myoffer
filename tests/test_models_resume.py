from app.models import ResumeModule


def test_default_sort_order_and_optional_title(db_session):
    module = ResumeModule(category="项目经历", content="内容A")
    db_session.add(module)
    db_session.commit()

    fetched = db_session.query(ResumeModule).filter_by(category="项目经历").one()
    assert fetched.sort_order == 0
    assert fetched.title is None
    assert fetched.content == "内容A"
