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
