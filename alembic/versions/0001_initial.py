"""initial schema: users + posts + seed

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.String(), nullable=True),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    users = sa.table(
        "users",
        sa.column("name", sa.String),
        sa.column("email", sa.String),
    )
    op.bulk_insert(
        users,
        [
            {"name": "Ana", "email": "ana@example.com"},
            {"name": "Luis", "email": "luis@example.com"},
        ],
    )


def downgrade():
    op.drop_table("posts")
    op.drop_table("users")
