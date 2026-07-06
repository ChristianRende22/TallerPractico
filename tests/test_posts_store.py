def test_create_post_success_minimal(client):
    payload = {"title": "Mi primer post", "content": "Contenido del post"}
    response = client.post("/posts/", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Mi primer post"
    assert data["content"] == "Contenido del post"
    assert data["status"] == "draft" # Default value
    assert "id" in data
    assert "created_at" in data

def test_create_post_success_with_status(client):
    payload = {"title": "Post publicado", "content": "Contenido", "status": "publish"}
    response = client.post("/posts/", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "publish"

def test_create_post_missing_title(client):
    payload = {"content": "Contenido sin titulo"}
    response = client.post("/posts/", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "title" for detail in data["details"])

def test_create_post_missing_content(client):
    payload = {"title": "Titulo sin contenido"}
    response = client.post("/posts/", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "content" for detail in data["details"])
