from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors.exceptions import PostNotFound, ValidationError
from app.models.post import Post
from app.models.post import POST_STATUSES
from app.schemas.post import Pagination, PostList, PostRead
from app.services.post_query import ORDERABLE, list_posts

router = APIRouter(prefix="/posts", tags=["posts"])


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
