from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    excerpt: str | None
    slug: str
    status: str
    author_id: int | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    deleted_at: datetime | None


class Pagination(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
