import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors.exceptions import PostNotFound, TrashPostLocked, ValidationError
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostRead, PostReplace, PostUpdate
from app.services.post_state import PostStateService

router = APIRouter(prefix="/posts", tags=["posts"])
_state_service = PostStateService()


def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise PostNotFound()
    return post


def _enforce_trash_lock(post: Post, incoming_fields: set[str]):
    if post.status == "trash" and incoming_fields - {"status"}:
        raise TrashPostLocked()


def _validate_author_id(db: Session, author_id: int | None):
    if author_id is not None and db.get(User, author_id) is None:
        raise ValidationError(
            details=[{"field": "author_id", "message": "author_id does not exist"}]
        )


def _validate_slug_unique(db: Session, slug: str | None, post_id: int):
    if slug is None:
        return
    existing = db.query(Post).filter(Post.slug == slug, Post.id != post_id).first()
    if existing is not None:
        raise ValidationError(
            details=[{"field": "slug", "message": "slug already in use"}]
        )


@router.patch("/{post_id}", response_model=PostRead)
def update_post(post_id: int, body: PostUpdate, db: Session = Depends(get_db)):
    post = _get_post_or_404(db, post_id)
    data = body.model_dump(exclude_unset=True)

    _enforce_trash_lock(post, set(data.keys()))
    _validate_author_id(db, data.get("author_id"))
    _validate_slug_unique(db, data.get("slug"), post.id)

    new_status = data.pop("status", None)
    for field, value in data.items():
        setattr(post, field, value)

    if new_status is not None and new_status != post.status:
        _state_service.transition(post, new_status)

    post.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    return post


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "post"


@router.put("/{post_id}", response_model=PostRead)
def replace_post(post_id: int, body: PostReplace, db: Session = Depends(get_db)):
    post = _get_post_or_404(db, post_id)
    data = body.model_dump(exclude_unset=True)

    _enforce_trash_lock(post, set(data.keys()))
    _validate_author_id(db, data.get("author_id"))

    slug = data.get("slug") or _slugify(body.title)
    _validate_slug_unique(db, slug, post.id)

    post.title = body.title
    post.content = body.content
    post.excerpt = data.get("excerpt")
    post.slug = slug
    if "author_id" in data:
        post.author_id = data["author_id"]

    new_status = data.get("status")
    if new_status is not None and new_status != post.status:
        _state_service.transition(post, new_status)

    post.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    return post
