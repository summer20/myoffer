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
