import re
from datetime import datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors.exceptions import PostNotFound, TrashPostLocked, ValidationError
from app.models.post import POST_STATUSES, Post
from app.models.user import User
from app.schemas.post import (
    Pagination,
    PostCreate,
    PostList,
    PostRead,
    PostReplace,
    PostUpdate,
)
from app.services.post_query import ORDERABLE, list_posts
from app.services.post_state import PostStateService

router = APIRouter(prefix="/posts", tags=["posts"])
_state_service = PostStateService()


@router.get("", response_model=PostList)
def index(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    author: int | None = Query(None),
    orderby: str = Query("created_at"),
    order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    details = []
    if status is not None and status not in POST_STATUSES:
        details.append({"field": "status", "message": f"Invalid status '{status}'"})
    if orderby not in ORDERABLE:
        details.append({"field": "orderby", "message": f"Invalid orderby '{orderby}'"})
    if order not in ("asc", "desc"):
        details.append({"field": "order", "message": f"Invalid order '{order}'"})
    if details:
        raise ValidationError(details=details)

    items, total = list_posts(
        db,
        search=search,
        status=status,
        author=author,
        orderby=orderby,
        order=order,
        page=page,
        per_page=per_page,
    )
    total_pages = ceil(total / per_page) if total else 0
    return PostList(
        data=items,
        pagination=Pagination(
            total=total, page=page, per_page=per_page, total_pages=total_pages
        ),
    )


@router.get("/{id}", response_model=PostRead)
def show(id: int, db: Session = Depends(get_db)):
    post = db.get(Post, id)
    if post is None or post.status == "trash":
        raise PostNotFound()
    return post


def generate_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')


@router.post("/", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(post_in: PostCreate, db: Session = Depends(get_db)):
    db_post = Post(
        title=post_in.title,
        content=post_in.content,
        status=post_in.status,
        slug=generate_slug(post_in.title)
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


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

@router.delete("/{id}")
def delete_post(
    id: int,
    force: bool = Query(False, description="Si es true, elimina el registro permanentemente"),
    db: Session = Depends(get_db),
):
    """
    DELETE /posts/{id}          -> soft delete (status=trash), 200 + PostRead
    DELETE /posts/{id}?force=true -> hard delete, 204 sin body
    """
    post = db.query(Post).filter(Post.id == id).first()
    if post is None:
        raise PostNotFound()

    if force:
        db.delete(post)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    service = PostStateService()
    post = service.transition(post, "trash")
    db.commit()
    db.refresh(post)

    return PostRead.model_validate(post)