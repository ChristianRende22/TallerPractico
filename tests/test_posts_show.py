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


def test_show_post_success(client, db_session):
    post = _post(db_session, slug="a")

    response = client.get(f"/posts/{post.id}")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == CANONICAL_FIELDS
    assert body["id"] == post.id
    assert body["slug"] == "a"
    assert body["status"] == "draft"


def test_show_post_not_found(client):
    response = client.get("/posts/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "POST_NOT_FOUND"
    assert body["status"] == 404


def test_show_post_in_trash_returns_not_found(client, db_session):
    post = _post(db_session, slug="trash", status="trash")

    response = client.get(f"/posts/{post.id}")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "POST_NOT_FOUND"
    assert body["status"] == 404