from app.models.post import Post

CANONICAL_FIELDS = {
    "id",
    "title",
    "content",
    "excerpt",
    "slug",
    "status",
    "author_id",
    "created_at",
    "updated_at",
    "published_at",
    "deleted_at",
}


def _post(db, slug, **kw):
    defaults = {"title": "t", "content": "c", "status": "draft"}
    defaults.update(kw)
    post = Post(slug=slug, **defaults)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def test_index_returns_paginated(client, db_session):
    for i in range(15):
        _post(db_session, slug=f"s{i}")
    response = client.get("/posts")
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 10
    assert body["pagination"] == {
        "total": 15,
        "page": 1,
        "per_page": 10,
        "total_pages": 2,
    }


def test_index_second_page(client, db_session):
    for i in range(15):
        _post(db_session, slug=f"s{i}")
    body = client.get("/posts?page=2").json()
    assert len(body["data"]) == 5
    assert body["pagination"]["page"] == 2


def test_index_post_has_canonical_shape(client, db_session):
    _post(db_session, slug="a")
    body = client.get("/posts").json()
    assert set(body["data"][0].keys()) == CANONICAL_FIELDS


def test_index_hides_trash_by_default(client, db_session):
    _post(db_session, slug="a", status="draft")
    _post(db_session, slug="b", status="trash")
    body = client.get("/posts").json()
    assert body["pagination"]["total"] == 1
    assert all(p["status"] != "trash" for p in body["data"])


def test_index_status_trash(client, db_session):
    _post(db_session, slug="a", status="draft")
    _post(db_session, slug="b", status="trash")
    body = client.get("/posts?status=trash").json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["status"] == "trash"


def test_index_search(client, db_session):
    _post(db_session, slug="a", title="Hola Mundo")
    _post(db_session, slug="b", title="Nada", content="nope")
    body = client.get("/posts?search=hola").json()
    assert body["pagination"]["total"] == 1


def test_index_filter_author(client, db_session):
    from app.models.user import User

    user = User(name="Ana", email="a@e.com")
    db_session.add(user)
    db_session.commit()
    _post(db_session, slug="a", author_id=user.id)
    _post(db_session, slug="b")
    body = client.get(f"/posts?author={user.id}").json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["author_id"] == user.id


def test_index_orderby_title_asc(client, db_session):
    _post(db_session, slug="a", title="Banana")
    _post(db_session, slug="b", title="Apple")
    body = client.get("/posts?orderby=title&order=asc").json()
    assert [p["title"] for p in body["data"]] == ["Apple", "Banana"]


def test_index_invalid_per_page_returns_400(client):
    response = client.get("/posts?per_page=999")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "per_page" for d in body["details"])


def test_index_invalid_status_returns_400(client):
    response = client.get("/posts?status=xyz")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "status" for d in body["details"])


def test_index_invalid_orderby_returns_400(client):
    response = client.get("/posts?orderby=hackme")
    assert response.status_code == 400
    assert any(d["field"] == "orderby" for d in response.json()["details"])


def test_index_empty_db(client):
    body = client.get("/posts").json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 0
    assert body["pagination"]["total_pages"] == 0
