import re
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.post import Post
from app.schemas.post import PostCreate, PostRead

# Router base de /posts. Vacío en Spec 0.
# P2–P6 agregan aquí sus endpoints; no se toca la fundación.
router = APIRouter(prefix="/posts", tags=["posts"])

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
