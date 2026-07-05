from datetime import datetime

from app.models.post import Post
from app.models.user import User

CANONICAL_FIELDS = {
    "id", "title", "content", "excerpt", "slug", "status", "author_id",
    "created_at", "updated_at", "published_at", "deleted_at",
}


def _seed_post(db_session, **overrides):
    user = db_session.query(User).first()
    if user is None:
        user = User(name="Ana", email="ana@example.com")
        db_session.add(user)
        db_session.commit()
    defaults = dict(
        title="Original", content="Contenido", slug="original", author_id=user.id
    )
    defaults.update(overrides)
    post = Post(**defaults)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


def test_patch_updates_only_sent_fields(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"title": "Nuevo"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Nuevo"
    assert body["content"] == "Contenido"


def test_patch_nonexistent_post_returns_404(client):
    response = client.patch("/posts/9999", json={"title": "x"})
    assert response.status_code == 404
    assert response.json()["code"] == "POST_NOT_FOUND"


def test_put_replaces_content_fields(client, db_session):
    post = _seed_post(db_session)
    response = client.put(f"/posts/{post.id}", json={"title": "T2", "content": "C2"})
    assert response.status_code == 200
    assert response.json()["title"] == "T2"


def test_patch_empty_body_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_patch_empty_title_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"title": ""})
    assert response.status_code == 400


def test_put_missing_title_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.put(f"/posts/{post.id}", json={"content": "C2"})
    assert response.status_code == 400


def test_patch_invalid_author_id_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"author_id": 9999})
    assert response.status_code == 400
    assert any(d["field"] == "author_id" for d in response.json()["details"])


def test_patch_duplicate_slug_returns_400(client, db_session):
    post_a = _seed_post(db_session, slug="post-a")
    _seed_post(db_session, slug="post-b")
    response = client.patch(f"/posts/{post_a.id}", json={"slug": "post-b"})
    assert response.status_code == 400
    assert any(d["field"] == "slug" for d in response.json()["details"])


def test_patch_field_on_trashed_post_returns_422(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "trash"})
    response = client.patch(f"/posts/{post.id}", json={"title": "x"})
    assert response.status_code == 422
    assert response.json()["code"] == "TRASH_POST_LOCKED"


def test_patch_restore_and_edit_together_returns_422(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "trash"})
    response = client.patch(f"/posts/{post.id}", json={"status": "draft", "title": "x"})
    assert response.status_code == 422


def test_patch_restore_only_status_succeeds(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "trash"})
    response = client.patch(f"/posts/{post.id}", json={"status": "draft"})
    assert response.status_code == 200
    assert response.json()["deleted_at"] is None


def test_patch_publish_sets_published_at(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"status": "publish"})
    assert response.status_code == 200
    assert response.json()["published_at"] is not None


def test_put_without_status_preserves_it(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "publish"})
    response = client.put(f"/posts/{post.id}", json={"title": "T2", "content": "C2"})
    assert response.json()["status"] == "publish"


def test_put_without_author_id_preserves_it(client, db_session):
    post = _seed_post(db_session)
    response = client.put(f"/posts/{post.id}", json={"title": "T2", "content": "C2"})
    assert response.json()["author_id"] == post.author_id


def test_put_without_slug_regenerates_it(client, db_session):
    post = _seed_post(db_session, slug="original")
    response = client.put(
        f"/posts/{post.id}", json={"title": "Nuevo Titulo", "content": "C2"}
    )
    assert response.json()["slug"] != "original"


def test_patch_noop_status_bumps_updated_at(client, db_session):
    post = _seed_post(db_session)
    original_updated_at = post.updated_at
    response = client.patch(f"/posts/{post.id}", json={"status": "draft"})
    assert response.status_code == 200
    new_updated_at = datetime.fromisoformat(response.json()["updated_at"])
    assert new_updated_at > original_updated_at


def test_response_has_exactly_11_fields(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"title": "x"})
    assert set(response.json().keys()) == CANONICAL_FIELDS


def test_id_and_created_at_are_immutable(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(
        f"/posts/{post.id}",
        json={"title": "cambio real", "id": 9999, "created_at": "2000-01-01T00:00:00"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == post.id
