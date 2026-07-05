from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    slug: str | None = None
    author_id: int | None = None
    status: str | None = None

    @field_validator("title", "content", "excerpt", "slug")
    @classmethod
    def _not_blank(cls, value):
        if value is not None and value.strip() == "":
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _at_least_one_field(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided")
        return self


class PostReplace(BaseModel):
    title: str
    content: str
    excerpt: str | None = None
    slug: str | None = None
    author_id: int | None = None
    status: str | None = None

    @field_validator("title", "content")
    @classmethod
    def _not_blank_required(cls, value):
        if value.strip() == "":
            raise ValueError("must not be empty")
        return value

    @field_validator("excerpt", "slug")
    @classmethod
    def _not_blank_optional(cls, value):
        if value is not None and value.strip() == "":
            raise ValueError("must not be empty")
        return value
