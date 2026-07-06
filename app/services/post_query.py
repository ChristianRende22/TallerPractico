from sqlalchemy import func, or_

from app.models.post import Post

ORDERABLE = {
    "created_at": Post.created_at,
    "updated_at": Post.updated_at,
    "title": Post.title,
    "id": Post.id,
}


def list_posts(
    db,
    *,
    search=None,
    status=None,
    author=None,
    orderby="created_at",
    order="desc",
    page=1,
    per_page=10,
):
    query = db.query(Post)

    if status is None:
        query = query.filter(Post.status != "trash")
    else:
        query = query.filter(Post.status == status)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Post.title).like(pattern),
                func.lower(Post.content).like(pattern),
            )
        )

    if author is not None:
        query = query.filter(Post.author_id == author)

    total = query.count()

    column = ORDERABLE.get(orderby, Post.created_at)
    column = column.desc() if order == "desc" else column.asc()

    items = (
        query.order_by(column)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return items, total
