# Spec 0 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir los cimientos compartidos de la API CMS de Posts (schema BD, contrato JSON canónico, formato de error estándar, ruteo base, `GET /health` e interfaz de `PostStateService`) que desbloquean las 5 specs siguientes.

**Architecture:** App FastAPI creada por factory `create_app()`. SQLAlchemy 2.0 (estilo `Mapped`) para modelos, Alembic para migraciones + seed, Pydantic v2 para el contrato de salida. Un handler global de errores traduce toda excepción al formato JSON estándar, incluyendo la validación nativa de FastAPI que se reescribe a 400. Tests con pytest sobre SQLite en memoria (StaticPool) heredando fixtures compartidas.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest, httpx (TestClient).

## Global Constraints

- Python 3.11+ (usa sintaxis `X | None`).
- Version floors: `fastapi>=0.110`, `sqlalchemy>=2.0`, `alembic>=1.13`, `pydantic>=2.6`, `pytest>=8.0`, `httpx>=0.27`, `uvicorn>=0.27`.
- **Contrato canónico de Post:** exactamente 11 campos, estos nombres, sin extras ni faltantes: `id, title, content, excerpt, slug, status, author_id, created_at, updated_at, published_at, deleted_at`.
- **Formato de error:** siempre `{error, code, status}` (+ `details` opcional). Códigos: `VALIDATION_ERROR` (400), `POST_NOT_FOUND` (404), `INVALID_STATUS_TRANSITION` (422), `TRASH_POST_LOCKED` (422), `INTERNAL_ERROR` (500).
- **Validación de body → 400** `VALIDATION_ERROR` (nunca el 422 nativo de FastAPI). El 422 se reserva a reglas de negocio.
- **Estados:** `POST_STATUSES = ("draft", "pending", "publish", "private", "trash")`, fuente única de verdad en `app/models/post.py`.
- La fundación queda congelada tras Spec 0; P2–P6 solo tocan `routers/posts.py`, sus `schemas/` y sus `tests/`.
- Commit por tarea (test en verde). Nadie commitea con tests rojos.

## File Structure

- `requirements.txt` — dependencias.
- `app/main.py` — factory `create_app()`, monta routers y registra error handlers.
- `app/database.py` — engine, `SessionLocal`, `Base`, `get_db()`.
- `app/models/user.py`, `app/models/post.py` — modelos + `POST_STATUSES`.
- `app/schemas/post.py` — `PostRead`, `Pagination`.
- `app/routers/health.py` — `GET /health`. `app/routers/posts.py` — router `/posts` vacío.
- `app/errors/exceptions.py` — `AppError` + subclases. `app/errors/handlers.py` — handlers globales.
- `app/services/post_state.py` — interfaz `PostStateService` (stub).
- `alembic/` — migración inicial + seed.
- `tests/conftest.py` — fixtures compartidas. `tests/test_*.py` — tests por área.

---

### Task 1: Bootstrap de la app + health check + fixtures base

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py`, `app/main.py`
- Create: `app/routers/__init__.py`, `app/routers/health.py`, `app/routers/posts.py`
- Test: `tests/__init__.py`, `tests/conftest.py`, `tests/test_health.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI` en `app/main.py`; fixture `client` (TestClient) en `tests/conftest.py`; `app.routers.posts.router` (APIRouter con `prefix="/posts"`, vacío).

- [ ] **Step 1: Escribir `requirements.txt`**

```
fastapi>=0.110
uvicorn>=0.27
sqlalchemy>=2.0
alembic>=1.13
pydantic>=2.6
httpx>=0.27
pytest>=8.0
```

- [ ] **Step 2: Instalar dependencias**

Run: `python -m pip install -r requirements.txt`
Expected: instalación sin errores.

- [ ] **Step 3: Escribir el test que falla**

`tests/__init__.py` vacío. `tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)
```

`tests/test_health.py`:

```python
def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Correr el test y verificar que falla**

Run: `python -m pytest tests/test_health.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app').

- [ ] **Step 5: Implementar el código mínimo**

`app/__init__.py` vacío. `app/routers/__init__.py` vacío.

`app/routers/health.py`:

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}
```

`app/routers/posts.py`:

```python
from fastapi import APIRouter

# Router base de /posts. Vacío en Spec 0.
# P2–P6 agregan aquí sus endpoints; no se toca la fundación.
router = APIRouter(prefix="/posts", tags=["posts"])
```

`app/main.py`:

```python
from fastapi import FastAPI

from app.routers import health, posts


def create_app() -> FastAPI:
    app = FastAPI(title="CMS Posts API")
    app.include_router(health.router)
    app.include_router(posts.router)
    return app


app = create_app()
```

- [ ] **Step 6: Correr el test y verificar que pasa**

Run: `python -m pytest tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt app/ tests/
git commit -m "feat: bootstrap FastAPI app con health check y fixtures base"
```

---

### Task 2: Capa de base de datos + modelos User y Post

**Files:**
- Create: `app/database.py`
- Create: `app/models/__init__.py`, `app/models/user.py`, `app/models/post.py`
- Modify: `tests/conftest.py` (agregar fixtures de BD y override de `get_db`)
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: `create_app` (Task 1).
- Produces: `app.database.Base`, `app.database.get_db`, `app.database.engine`, `app.database.SessionLocal`; `app.models.user.User`; `app.models.post.Post`; `app.models.post.POST_STATUSES`; fixtures `db_engine`, `db_session`, `client` (override de `get_db`).

- [ ] **Step 1: Escribir el test que falla**

`tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL (No module named 'app.database' / 'app.models').

- [ ] **Step 3: Implementar `app/database.py`**

```python
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./posts.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _connection_record):
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Implementar los modelos**

`app/models/__init__.py` (registra ambos en el metadata):

```python
from app.models.post import Post  # noqa: F401
from app.models.user import User  # noqa: F401
```

`app/models/user.py`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
```

`app/models/post.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

POST_STATUSES = ("draft", "pending", "publish", "private", "trash")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String, nullable=True)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 5: Actualizar `tests/conftest.py`**

Reemplazar el contenido completo por:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra modelos en Base.metadata)
from app.database import Base, get_db
from app.main import create_app


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_models.py tests/test_health.py -v`
Expected: PASS (todos, incluido health que sigue verde).

- [ ] **Step 7: Commit**

```bash
git add app/database.py app/models/ tests/conftest.py tests/test_models.py
git commit -m "feat: capa de BD y modelos User/Post con FK y POST_STATUSES"
```

---

### Task 3: Migración Alembic inicial + seed de usuarios

**Files:**
- Create: `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/0001_initial.py`
- Test: `tests/test_migration_and_seed.py`

**Interfaces:**
- Consumes: `app.database.Base`, modelos (Task 2).
- Produces: migración `0001` que crea `users` + `posts` y siembra 2 usuarios (`Ana`, `Luis`). `env.py` lee `DATABASE_URL` del entorno.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_migration_and_seed.py`:

```python
import os
import sqlite3
import subprocess
import sys


def test_migration_creates_schema_and_seed(tmp_path):
    db_path = tmp_path / "mig.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    con = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"users", "posts"} <= tables

    names = [row[0] for row in con.execute("SELECT name FROM users ORDER BY id")]
    assert names == ["Ana", "Luis"]
    con.close()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/test_migration_and_seed.py -v`
Expected: FAIL (alembic no configurado / returncode != 0).

- [ ] **Step 3: Crear `alembic.ini`**

```ini
[alembic]
script_location = alembic

[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 4: Crear `alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Crear `alembic/env.py`**

```python
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (registra modelos)
from app.database import Base

config = context.config

db_url = os.environ.get("DATABASE_URL", "sqlite:///./posts.db")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6: Crear la migración `alembic/versions/0001_initial.py`**

```python
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
```

- [ ] **Step 7: Correr el test y verificar que pasa**

Run: `python -m pytest tests/test_migration_and_seed.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add alembic.ini alembic/ tests/test_migration_and_seed.py
git commit -m "feat: migración inicial Alembic (users+posts) con seed de usuarios"
```

---

### Task 4: Handler global de errores + traducción Pydantic → 400

**Files:**
- Create: `app/errors/__init__.py`, `app/errors/exceptions.py`, `app/errors/handlers.py`
- Modify: `app/main.py` (registrar handlers)
- Test: `tests/test_error_format.py`

**Interfaces:**
- Consumes: nada de tareas previas (independiente).
- Produces: `app.errors.exceptions.AppError`, `ValidationError`, `PostNotFound`, `InvalidStatusTransition`, `TrashPostLocked`; `app.errors.handlers.register_error_handlers(app)`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_error_format.py`:

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors.exceptions import PostNotFound
from app.errors.handlers import register_error_handlers


class _Item(BaseModel):
    title: str


@pytest.fixture
def error_client():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom-notfound")
    def boom_notfound():
        raise PostNotFound()

    @app.get("/boom-500")
    def boom_500():
        raise RuntimeError("kaboom")

    @app.post("/need-title")
    def need_title(item: _Item):
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


def test_app_error_shape(error_client):
    response = error_client.get("/boom-notfound")
    assert response.status_code == 404
    assert response.json() == {
        "error": "Post not found",
        "code": "POST_NOT_FOUND",
        "status": 404,
    }


def test_internal_error_shape(error_client):
    response = error_client.get("/boom-500")
    assert response.status_code == 500
    assert response.json() == {
        "error": "Internal server error",
        "code": "INTERNAL_ERROR",
        "status": 500,
    }


def test_pydantic_validation_translated_to_400(error_client):
    response = error_client.post("/need-title", json={})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["status"] == 400
    assert any(detail["field"] == "title" for detail in body["details"])
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/test_error_format.py -v`
Expected: FAIL (No module named 'app.errors').

- [ ] **Step 3: Implementar `app/errors/exceptions.py`**

`app/errors/__init__.py` vacío. `app/errors/exceptions.py`:

```python
class AppError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class ValidationError(AppError):
    def __init__(self, message="Validation failed", details=None):
        super().__init__(400, "VALIDATION_ERROR", message, details)


class PostNotFound(AppError):
    def __init__(self, message="Post not found"):
        super().__init__(404, "POST_NOT_FOUND", message)


class InvalidStatusTransition(AppError):
    def __init__(self, message="Invalid status transition"):
        super().__init__(422, "INVALID_STATUS_TRANSITION", message)


class TrashPostLocked(AppError):
    def __init__(self, message="Post in trash cannot be updated"):
        super().__init__(422, "TRASH_POST_LOCKED", message)
```

- [ ] **Step 4: Implementar `app/errors/handlers.py`**

```python
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors.exceptions import AppError


def _payload(error, code, status, details=None):
    body = {"error": error, "code": code, "status": status}
    if details is not None:
        body["details"] = details
    return body


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        content=_payload(exc.message, exc.code, exc.status, exc.details),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(p) for p in error["loc"] if p != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content=_payload("Validation failed", "VALIDATION_ERROR", 400, details),
    )


async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_payload("Internal server error", "INTERNAL_ERROR", 500),
    )


def register_error_handlers(app):
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
```

- [ ] **Step 5: Registrar handlers en `app/main.py`**

Reemplazar `app/main.py` por:

```python
from fastapi import FastAPI

from app.errors.handlers import register_error_handlers
from app.routers import health, posts


def create_app() -> FastAPI:
    app = FastAPI(title="CMS Posts API")
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(posts.router)
    return app


app = create_app()
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_error_format.py tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/errors/ app/main.py tests/test_error_format.py
git commit -m "feat: handler global de errores + traduccion Pydantic a 400"
```

---

### Task 5: Schemas Pydantic PostRead + Pagination

**Files:**
- Create: `app/schemas/__init__.py`, `app/schemas/post.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: `app.models.post.Post` (Task 2), fixture `db_session` (Task 2).
- Produces: `app.schemas.post.PostRead` (11 campos canónicos, `from_attributes=True`), `app.schemas.post.Pagination`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_schemas.py`:

```python
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/test_schemas.py -v`
Expected: FAIL (No module named 'app.schemas').

- [ ] **Step 3: Implementar `app/schemas/post.py`**

`app/schemas/__init__.py` vacío. `app/schemas/post.py`:

```python
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
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/ tests/test_schemas.py
git commit -m "feat: schemas PostRead (contrato canonico) y Pagination"
```

---

### Task 6: Interfaz de PostStateService (stub de contrato)

**Files:**
- Create: `app/services/__init__.py`, `app/services/post_state.py`
- Test: `tests/test_post_state_stub.py`

**Interfaces:**
- Consumes: nada.
- Produces: `app.services.post_state.PostStateService` con `can_transition(post, new_status) -> bool` y `transition(post, new_status) -> Post`, ambos lanzando `NotImplementedError` hasta Spec 4.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_post_state_stub.py`:

```python
import pytest

from app.services.post_state import PostStateService


def test_can_transition_not_implemented():
    with pytest.raises(NotImplementedError):
        PostStateService().can_transition(object(), "publish")


def test_transition_not_implemented():
    with pytest.raises(NotImplementedError):
        PostStateService().transition(object(), "trash")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/test_post_state_stub.py -v`
Expected: FAIL (No module named 'app.services').

- [ ] **Step 3: Implementar `app/services/post_state.py`**

`app/services/__init__.py` vacío. `app/services/post_state.py`:

```python
class PostStateService:
    """Contrato de transiciones de estado de Post. Implementacion: Spec 4 (P5).

    Reglas acordadas (NO implementadas aqui):
    - draft/pending/private -> publish: exige title y content no vacios;
      setea published_at solo la primera vez.
    - cualquiera -> trash: setea deleted_at.
    - trash -> otro: limpia deleted_at (restauracion).
    - Regla dura: post en trash no acepta update de campos -> 422 TRASH_POST_LOCKED.

    Consumidores (P6/Delete) codean contra esta interfaz desde el dia 1.
    """

    def can_transition(self, post, new_status: str) -> bool:
        raise NotImplementedError("PostStateService.can_transition — Spec 4 (P5)")

    def transition(self, post, new_status: str):
        raise NotImplementedError("PostStateService.transition — Spec 4 (P5)")
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_post_state_stub.py -v`
Expected: PASS.

- [ ] **Step 5: Correr la suite completa (todo verde)**

Run: `python -m pytest -v`
Expected: PASS en todos los tests de Spec 0.

- [ ] **Step 6: Commit**

```bash
git add app/services/ tests/test_post_state_stub.py
git commit -m "feat: interfaz stub de PostStateService (contrato para Spec 4/5)"
```

---

## Definition of Done (Spec 0)

- [ ] Suite completa verde: `python -m pytest -v`
- [ ] `GET /health` responde `200 {"status":"ok"}`
- [ ] Migración Alembic crea `users`+`posts` con FK y siembra 2 usuarios
- [ ] `PostRead` expone exactamente los 11 campos canónicos
- [ ] Errores cumplen el formato estándar; validación de body → 400
- [ ] Interfaz `PostStateService` disponible como stub
- [ ] Todos los commits en `feat/spec-0-foundation`, main sin romperse
