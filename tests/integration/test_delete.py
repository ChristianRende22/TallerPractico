from datetime import datetime, timezone

from app.models.post import Post


def make_post(db_session, **overrides):
    """Helper mínimo para insertar un post de prueba directamente en la BD."""
    defaults = dict(
        title="Post de prueba",
        content="Contenido de prueba",
        excerpt=None,
        slug=f"post-prueba-{datetime.now(timezone.utc).timestamp()}",
        status="draft",
        author_id=1,
    )
    defaults.update(overrides)
    post = Post(**defaults)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post

def test_delete_post_soft_deletes_by_default(client, db_session):
    post = make_post(db_session, status="draft")

    response = client.delete(f"/posts/{post.id}")

    assert response.status_code == 200
    assert response.json()["status"] == "trash"


def test_delete_post_soft_delete_returns_post_contract(client, db_session):
    post = make_post(db_session, status="draft")

    response = client.delete(f"/posts/{post.id}")

    body = response.json()
    expected_fields = {
        "id", "title", "content", "excerpt", "slug", "status",
        "author_id", "created_at", "updated_at", "published_at", "deleted_at",
    }
    assert set(body.keys()) == expected_fields

def test_delete_post_soft_delete_keeps_record_in_database(client, db_session):
    post = make_post(db_session, status="draft")

    client.delete(f"/posts/{post.id}")

    db_session.expire_all()
    still_there = db_session.query(Post).filter(Post.id == post.id).first()
    assert still_there is not None
    assert still_there.status == "trash"

def test_soft_delete_already_trashed_post_is_idempotent(client, db_session):
    post = make_post(db_session, status="trash", deleted_at=datetime.now(timezone.utc))

    response = client.delete(f"/posts/{post.id}")

    assert response.status_code == 200
    assert response.json()["status"] == "trash"

    db_session.expire_all()
    still_there = db_session.query(Post).filter(Post.id == post.id).first()
    assert still_there is not None

def test_delete_post_force_true_permanently_deletes_record(client, db_session):
    post = make_post(db_session, status="draft")
    post_id = post.id

    client.delete(f"/posts/{post_id}?force=true")

    db_session.expire_all()
    gone = db_session.query(Post).filter(Post.id == post_id).first()
    assert gone is None


def test_delete_post_force_true_returns_204_no_content(client, db_session):
    post = make_post(db_session, status="draft")

    response = client.delete(f"/posts/{post.id}?force=true")

    assert response.status_code == 204
    assert response.content == b""

def test_force_delete_then_any_delete_returns_404(client, db_session):
    post = make_post(db_session, status="draft")
    post_id = post.id
    client.delete(f"/posts/{post_id}?force=true")

    response = client.delete(f"/posts/{post_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "POST_NOT_FOUND"

def test_delete_missing_post_returns_404(client, db_session):
    response = client.delete("/posts/999999")
    
    print(response.json())

    assert response.status_code == 404
    assert response.json() == {
        "error": "Post not found",
        "code": "POST_NOT_FOUND",
        "status": 404,
        "details": [],
    }


def test_force_delete_missing_post_returns_404(client, db_session):
    response = client.delete("/posts/999999?force=true")

    assert response.status_code == 404
    assert response.json()["code"] == "POST_NOT_FOUND"