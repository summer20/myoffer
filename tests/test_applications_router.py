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
