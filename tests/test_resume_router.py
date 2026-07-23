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
