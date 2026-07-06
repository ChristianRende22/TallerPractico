import pytest
from sqlalchemy.exc import IntegrityError

from app.models.post import POST_STATUSES, Post
from app.models.user import User


def test_post_statuses_constant():
    assert POST_STATUSES == ("draft", "pending", "publish", "private", "trash")


def test_user_and_post_persist(db_session):
    user = User(name="Ana", email="ana@example.com")
    db_session.add(user)
    db_session.commit()

    post = Post(title="T", content="C", slug="t", author_id=user.id)
    db_session.add(post)
    db_session.commit()

    assert post.id is not None
    assert post.status == "draft"


def test_fk_rejects_invalid_author(db_session):
    post = Post(title="T", content="C", slug="bad-author", author_id=999)
    db_session.add(post)
    with pytest.raises(IntegrityError):
        db_session.commit()
