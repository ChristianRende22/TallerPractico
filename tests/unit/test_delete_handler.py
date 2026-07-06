import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from fastapi import Response

from app.routers.posts import delete_post
from app.errors.exceptions import PostNotFound
from app.models.post import Post


def make_mock_post(**overrides):
    """Post en memoria con los 11 campos del contrato, sin tocar BD."""
    defaults = dict(
        id=1,
        title="Post de prueba",
        content="Contenido de prueba",
        excerpt=None,
        slug="post-prueba",
        status="draft",
        author_id=1,
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        published_at=None,
        deleted_at=None,
    )
    defaults.update(overrides)
    post = MagicMock(spec=Post)
    for key, value in defaults.items():
        setattr(post, key, value)
    return post


def make_mock_db(post_found):
    """Sesión mockeada cuyo query().filter().first() devuelve `post_found`."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = post_found
    return db

def test_delete_post_raises_post_not_found_when_missing():
    db = make_mock_db(post_found=None)

    with pytest.raises(PostNotFound):
        delete_post(id=999, force=False, db=db)


def test_delete_post_force_true_raises_post_not_found_when_missing():
    db = make_mock_db(post_found=None)

    with pytest.raises(PostNotFound):
        delete_post(id=999, force=True, db=db)


def test_delete_post_checks_existence_before_branching_on_force():
    """La existencia se valida antes de mirar `force`, para ambos modos."""
    db = make_mock_db(post_found=None)

    with pytest.raises(PostNotFound):
        delete_post(id=999, force=True, db=db)

    db.delete.assert_not_called()
    db.commit.assert_not_called()

def test_delete_post_force_true_calls_db_delete_and_commit():
    post = make_mock_post()
    db = make_mock_db(post_found=post)

    response = delete_post(id=post.id, force=True, db=db)

    db.delete.assert_called_once_with(post)
    db.commit.assert_called_once()
    assert isinstance(response, Response)
    assert response.status_code == 204


def test_delete_post_force_true_returns_empty_body():
    post = make_mock_post()
    db = make_mock_db(post_found=post)

    response = delete_post(id=post.id, force=True, db=db)

    assert response.body == b""


def test_delete_post_force_true_does_not_call_post_state_service():
    post = make_mock_post()
    db = make_mock_db(post_found=post)

    with patch("app.routers.posts.PostStateService.transition") as mock_transition:
        delete_post(id=post.id, force=True, db=db)

    mock_transition.assert_not_called()

def test_delete_post_soft_delete_calls_post_state_service_with_trash():
    post = make_mock_post(status="draft")
    db = make_mock_db(post_found=post)

    with patch("app.routers.posts.PostStateService.transition", return_value=post) as mock_transition:
        delete_post(id=post.id, force=False, db=db)

    mock_transition.assert_called_once_with(post, "trash")


def test_delete_post_soft_delete_commits_and_refreshes():
    post = make_mock_post(status="draft")
    db = make_mock_db(post_found=post)

    with patch("app.routers.posts.PostStateService.transition", return_value=post):
        delete_post(id=post.id, force=False, db=db)

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(post)


def test_delete_post_soft_delete_does_not_call_db_delete():
    """El soft delete nunca debe borrar el registro físico."""
    post = make_mock_post(status="draft")
    db = make_mock_db(post_found=post)

    with patch("app.routers.posts.PostStateService.transition", return_value=post):
        delete_post(id=post.id, force=False, db=db)

    db.delete.assert_not_called()


def test_delete_post_soft_delete_returns_post_read_contract():
    post = make_mock_post(status="trash", deleted_at=datetime(2026, 7, 6, tzinfo=timezone.utc))
    db = make_mock_db(post_found=post)

    with patch("app.routers.posts.PostStateService.transition", return_value=post):
        result = delete_post(id=post.id, force=False, db=db)

    # PostRead expone estos 11 campos vía model_dump/dict
    result_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
    expected_fields = {
        "id", "title", "content", "excerpt", "slug", "status",
        "author_id", "created_at", "updated_at", "published_at", "deleted_at",
    }
    assert set(result_dict.keys()) == expected_fields
    assert result_dict["status"] == "trash"