from app.models.post import Post
from app.models.user import User
from app.schemas.post import Pagination, PostRead

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


def test_postread_has_exactly_canonical_fields():
    assert set(PostRead.model_fields) == CANONICAL_FIELDS


def test_postread_serializes_from_orm(db_session):
    user = User(name="Ana", email="ana@example.com")
    db_session.add(user)
    db_session.commit()
    post = Post(title="Hola", content="C", slug="hola", author_id=user.id)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    data = PostRead.model_validate(post).model_dump()
    assert set(data.keys()) == CANONICAL_FIELDS
    assert data["title"] == "Hola"
    assert data["status"] == "draft"
    assert data["published_at"] is None


def test_pagination_fields():
    pagination = Pagination(total=42, page=1, per_page=10, total_pages=5)
    assert pagination.model_dump() == {
        "total": 42,
        "page": 1,
        "per_page": 10,
        "total_pages": 5,
    }
