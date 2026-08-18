from app.config import USERNAME, PASSWORD


def test_protected_route_redirects_to_login_when_not_authenticated(anon_client):
    response = anon_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_health_check_does_not_require_login(anon_client):
    response = anon_client.get("/health")
    assert response.status_code == 200


def test_static_assets_do_not_require_login(anon_client):
    response = anon_client.get("/static/style.css")
    assert response.status_code == 200


def test_login_page_itself_is_public(anon_client):
    response = anon_client.get("/login")
    assert response.status_code == 200


def test_login_with_correct_credentials_grants_access(anon_client):
    login_response = anon_client.post(
        "/login", data={"username": USERNAME, "password": PASSWORD}, follow_redirects=False
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/"

    home_response = anon_client.get("/", follow_redirects=False)
    assert home_response.status_code == 200


def test_login_with_wrong_credentials_does_not_grant_access(anon_client):
    login_response = anon_client.post(
        "/login", data={"username": USERNAME, "password": "wrong-password"}, follow_redirects=False
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/login?error=1"

    home_response = anon_client.get("/", follow_redirects=False)
    assert home_response.status_code == 303
    assert home_response.headers["location"] == "/login"


def test_logout_clears_session(anon_client):
    anon_client.post("/login", data={"username": USERNAME, "password": PASSWORD})
    assert anon_client.get("/", follow_redirects=False).status_code == 200

    anon_client.get("/logout")

    home_response = anon_client.get("/", follow_redirects=False)
    assert home_response.status_code == 303
    assert home_response.headers["location"] == "/login"
