# Spec 4 — Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar `PATCH /posts/{id}` y `PUT /posts/{id}`, e implementar por
completo `PostStateService` (motor de transiciones de estado), reemplazando el
stub publicado en Spec 0.

**Architecture:** Reutiliza la factory `create_app()`, la capa de BD y las
fixtures de Spec 0 sin modificarlas. Agrega lógica de negocio en
`app/routers/posts.py` (antes vacío), dos schemas de escritura en
`app/schemas/post.py`, e implementa `app/services/post_state.py`. Las
validaciones de shape (tipos, campos vacíos, body vacío) se resuelven con
validadores Pydantic — reutilizan el `validation_error_handler` global de
Spec 0 (que ya traduce `RequestValidationError` a `400 VALIDATION_ERROR`), sin
código nuevo de manejo de errores. Las reglas de negocio que necesitan la BD
(integridad de `author_id`, unicidad de `slug`, trash lock, transición de
estado) se resuelven a mano dentro de los handlers, lanzando las excepciones
ya definidas en Spec 0 (`ValidationError`, `TrashPostLocked`,
`InvalidStatusTransition`).

**Tech Stack:** el mismo de Spec 0 (Python 3.11+, FastAPI, SQLAlchemy 2.0,
Alembic, Pydantic v2, pytest, httpx). No se agregan dependencias nuevas.

## Global Constraints

- No se modifica la interfaz pública de `PostStateService`
  (`can_transition(post, new_status) -> bool`, `transition(post, new_status) -> Post`)
  — P6 (Delete) ya codea contra ella.
- Precedencia de validación, en este orden exacto: existencia → shape del
  body → campos requeridos/no vacíos → integridad referencial (`author_id`) →
  unicidad de `slug` → trash lock → transición de estado → aplicación.
- Trash lock: un post en `trash` con cualquier campo del body distinto de
  `status` se rechaza completo (`422 TRASH_POST_LOCKED`), sin aplicar nada.
- `PUT` exige `title`/`content`; preserva `status` y `author_id` si se omiten;
  resetea/regenera `excerpt`/`slug` si se omiten.
- `slug` duplicado en Update → `400 VALIDATION_ERROR`, nunca autosufijo.
- `updated_at` se reasigna a mano en toda request aceptada (`200`), incluidos
  los no-ops de estado — el modelo `Post.updated_at` no tiene `onupdate`.
- No existe todavía ninguna utilidad de slugs en el repo (Store/Spec 3 no está
  implementada en esta rama). Este plan agrega un helper mínimo de slugify
  **privado al router de Update**, no en `app/core/slug.py`, para no
  presuponer el diseño que Store le quiera dar a esa utilidad más adelante.
- Tests organizados en `tests/unit/`, `tests/integration/`, `tests/e2e/`
  (a diferencia de los tests flat de Spec 0), según ya había decidido el spec.
- Commit por tarea (test en verde). Nadie commitea con tests rojos.

## File Structure

*(Mapa de archivos movido desde `doc/ai/plans/04-update.md` — la spec ya no lo
incluye porque es una decisión de arquitectura, no de negocio.)*

- `app/schemas/post.py` — se le agregan `PostUpdate`, `PostReplace` `[P5 extiende]`.
- `app/routers/posts.py` — se le agregan `PATCH /posts/{id}` y `PUT /posts/{id}` `[P5 trabaja acá]`.
- `app/services/post_state.py` — implementación completa, reemplaza el stub `[P5 — FROZEN para P6 tras merge]`.
- `app/errors/exceptions.py` — `InvalidStatusTransition`, `TrashPostLocked` ya definidas en Spec 0, sin cambios.
- `tests/unit/test_post_state_service.py` — reemplaza a `tests/test_post_state_stub.py`.
- `tests/integration/test_update.py` — tests de integración de `PATCH`/`PUT` vía `TestClient`.
- `tests/e2e/test_update_e2e.py` — escenario de punta a punta.
- `postman/CMS-Posts-Spec4-Update.postman_collection.json` — colección manual (no TDD), ver Task 7.

---

### Task 1: Motor de transiciones de estado (`PostStateService`)

**Files:**
- Modify: `app/services/post_state.py`
- Create: `tests/unit/__init__.py`, `tests/unit/test_post_state_service.py`
- Delete: `tests/test_post_state_stub.py` (sus asserts de `NotImplementedError` dejan de ser válidos)

**Interfaces:**
- Produces: `PostStateService.can_transition(post, new_status) -> bool`,
  `PostStateService.transition(post, new_status) -> Post` (misma firma que el
  stub de Spec 0, ahora con lógica real).

- [ ] **Step 1: Escribir los tests que fallan**

`tests/unit/__init__.py` vacío. `tests/unit/test_post_state_service.py`:

```python
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.errors.exceptions import InvalidStatusTransition
from app.services.post_state import PostStateService


def _post(**overrides):
    base = dict(
        status="draft", title="T", content="C", published_at=None, deleted_at=None
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.parametrize(
    "current,new",
    [
        ("draft", "publish"),
        ("pending", "trash"),
        ("trash", "draft"),
        ("publish", "publish"),
        ("trash", "trash"),
    ],
)
def test_can_transition_true_for_any_pair(current, new):
    assert PostStateService().can_transition(_post(status=current), new) is True


def test_can_transition_false_only_for_publish_with_empty_fields():
    assert PostStateService().can_transition(_post(content=""), "publish") is False
    assert PostStateService().can_transition(_post(title=""), "publish") is False


def test_transition_to_publish_sets_published_at_first_time():
    post = _post(status="draft")
    PostStateService().transition(post, "publish")
    assert post.status == "publish"
    assert post.published_at is not None


def test_transition_to_publish_again_keeps_original_published_at():
    original = datetime(2026, 1, 1, tzinfo=timezone.utc)
    post = _post(status="publish", published_at=original)
    PostStateService().transition(post, "publish")
    assert post.published_at == original


def test_transition_to_publish_raises_when_content_empty():
    post = _post(status="draft", content="")
    with pytest.raises(InvalidStatusTransition):
        PostStateService().transition(post, "publish")


def test_transition_to_trash_sets_deleted_at():
    post = _post(status="draft")
    PostStateService().transition(post, "trash")
    assert post.status == "trash"
    assert post.deleted_at is not None


def test_transition_out_of_trash_clears_deleted_at():
    post = _post(status="trash", deleted_at=datetime.now(timezone.utc))
    PostStateService().transition(post, "draft")
    assert post.status == "draft"
    assert post.deleted_at is None


def test_same_status_noop_does_not_touch_dates():
    post = _post(status="trash", deleted_at=None)
    PostStateService().transition(post, "trash")
    assert post.deleted_at is None
```

Borrar `tests/test_post_state_stub.py`.

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m pytest tests/unit/test_post_state_service.py -v`
Expected: FAIL (`NotImplementedError`, el stub todavía no tiene lógica).

- [ ] **Step 3: Implementar `app/services/post_state.py`**

```python
from datetime import datetime, timezone

from app.errors.exceptions import InvalidStatusTransition


class PostStateService:
    """Motor de transiciones de estado de Post. Implementado en Spec 4 (P5)."""

    def can_transition(self, post, new_status: str) -> bool:
        if new_status == "publish":
            return bool(post.title) and bool(post.content)
        return True

    def transition(self, post, new_status: str):
        if new_status == post.status:
            return post

        if new_status == "publish":
            if not self.can_transition(post, new_status):
                raise InvalidStatusTransition(
                    "Cannot publish a post with empty title or content"
                )
            if post.published_at is None:
                post.published_at = datetime.now(timezone.utc)

        if new_status == "trash":
            post.deleted_at = datetime.now(timezone.utc)
        elif post.status == "trash":
            post.deleted_at = None

        post.status = new_status
        return post
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/unit/test_post_state_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/post_state.py tests/unit/ 
git rm tests/test_post_state_stub.py
git commit -m "feat: implementar motor de transiciones de PostStateService"
```

---

### Task 2: Schemas de escritura + esqueleto de endpoints (happy path)

**Files:**
- Modify: `app/schemas/post.py` (agrega `PostUpdate`, `PostReplace`)
- Modify: `app/routers/posts.py` (agrega `PATCH`/`PUT` con lo mínimo: 404 + happy path)
- Create: `tests/integration/__init__.py`, `tests/integration/test_update.py`

**Interfaces:**
- Consumes: fixtures `client`, `db_session` (Spec 0), modelos `Post`/`User`.
- Produces: `app.schemas.post.PostUpdate`, `app.schemas.post.PostReplace`.

- [ ] **Step 1: Escribir los tests que fallan**

`tests/integration/__init__.py` vacío. `tests/integration/test_update.py`:

```python
from app.models.post import Post
from app.models.user import User


def _seed_post(db_session, **overrides):
    user = db_session.query(User).first()
    if user is None:
        user = User(name="Ana", email="ana@example.com")
        db_session.add(user)
        db_session.commit()
    defaults = dict(
        title="Original", content="Contenido", slug="original", author_id=user.id
    )
    defaults.update(overrides)
    post = Post(**defaults)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


def test_patch_updates_only_sent_fields(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"title": "Nuevo"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Nuevo"
    assert body["content"] == "Contenido"


def test_patch_nonexistent_post_returns_404(client):
    response = client.patch("/posts/9999", json={"title": "x"})
    assert response.status_code == 404
    assert response.json()["code"] == "POST_NOT_FOUND"


def test_put_replaces_content_fields(client, db_session):
    post = _seed_post(db_session)
    response = client.put(f"/posts/{post.id}", json={"title": "T2", "content": "C2"})
    assert response.status_code == 200
    assert response.json()["title"] == "T2"
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: FAIL (405/404 — no hay rutas `PATCH`/`PUT` todavía).

- [ ] **Step 3: Implementar los schemas**

Agregar a `app/schemas/post.py`:

```python
class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    slug: str | None = None
    author_id: int | None = None
    status: str | None = None


class PostReplace(BaseModel):
    title: str
    content: str
    excerpt: str | None = None
    slug: str | None = None
    author_id: int | None = None
    status: str | None = None
```

- [ ] **Step 4: Implementar el esqueleto de endpoints en `app/routers/posts.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors.exceptions import PostNotFound
from app.models.post import Post
from app.schemas.post import PostRead, PostReplace, PostUpdate

router = APIRouter(prefix="/posts", tags=["posts"])


def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise PostNotFound()
    return post


@router.patch("/{post_id}", response_model=PostRead)
def update_post(post_id: int, body: PostUpdate, db: Session = Depends(get_db)):
    post = _get_post_or_404(db, post_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post


@router.put("/{post_id}", response_model=PostRead)
def replace_post(post_id: int, body: PostReplace, db: Session = Depends(get_db)):
    post = _get_post_or_404(db, post_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/post.py app/routers/posts.py tests/integration/
git commit -m "feat: schemas de escritura y esqueleto PATCH/PUT /posts/{id}"
```

---

### Task 3: Validaciones de shape y campos requeridos/no vacíos

**Files:**
- Modify: `app/schemas/post.py` (validadores Pydantic)
- Modify: `tests/integration/test_update.py`

**Interfaces:**
- Consumes: `validation_error_handler` global de Spec 0 (sin cambios) — los
  `ValueError` de los validadores Pydantic ya se traducen a `400 VALIDATION_ERROR`.

- [ ] **Step 1: Agregar los tests que fallan**

Agregar a `tests/integration/test_update.py`:

```python
def test_patch_empty_body_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_patch_empty_title_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"title": ""})
    assert response.status_code == 400


def test_put_missing_title_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.put(f"/posts/{post.id}", json={"content": "C2"})
    assert response.status_code == 400
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: FAIL (body vacío y title vacío pasan de largo hoy).

- [ ] **Step 3: Agregar los validadores a `app/schemas/post.py`**

```python
from pydantic import BaseModel, field_validator, model_validator


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
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/post.py tests/integration/test_update.py
git commit -m "feat: validar shape y campos no vacios en PostUpdate/PostReplace"
```

---

### Task 4: Integridad referencial (`author_id`) y unicidad de `slug`

**Files:**
- Modify: `app/routers/posts.py`
- Modify: `tests/integration/test_update.py`

- [ ] **Step 1: Agregar los tests que fallan**

```python
def test_patch_invalid_author_id_returns_400(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"author_id": 9999})
    assert response.status_code == 400
    assert any(d["field"] == "author_id" for d in response.json()["details"])


def test_patch_duplicate_slug_returns_400(client, db_session):
    post_a = _seed_post(db_session, slug="post-a")
    _seed_post(db_session, slug="post-b")
    response = client.patch(f"/posts/{post_a.id}", json={"slug": "post-b"})
    assert response.status_code == 400
    assert any(d["field"] == "slug" for d in response.json()["details"])
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: FAIL (hoy no se valida ninguna de las dos reglas).

- [ ] **Step 3: Implementar los helpers de validación en `app/routers/posts.py`**

```python
from app.errors.exceptions import PostNotFound, ValidationError
from app.models.user import User


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
```

Llamarlos al principio de `update_post` y `replace_post`, antes de aplicar
ningún campo:

```python
data = body.model_dump(exclude_unset=True)
_validate_author_id(db, data.get("author_id"))
_validate_slug_unique(db, data.get("slug"), post.id)
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/posts.py tests/integration/test_update.py
git commit -m "feat: validar integridad de author_id y unicidad de slug en Update"
```

---

### Task 5: Trash lock + integración del motor de transición

**Files:**
- Modify: `app/routers/posts.py`
- Modify: `tests/integration/test_update.py`

**Interfaces:**
- Consumes: `PostStateService` (Task 1), `TrashPostLocked`/`InvalidStatusTransition` (Spec 0).

- [ ] **Step 1: Agregar los tests que fallan**

```python
def test_patch_field_on_trashed_post_returns_422(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "trash"})
    response = client.patch(f"/posts/{post.id}", json={"title": "x"})
    assert response.status_code == 422
    assert response.json()["code"] == "TRASH_POST_LOCKED"


def test_patch_restore_and_edit_together_returns_422(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "trash"})
    response = client.patch(f"/posts/{post.id}", json={"status": "draft", "title": "x"})
    assert response.status_code == 422


def test_patch_restore_only_status_succeeds(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "trash"})
    response = client.patch(f"/posts/{post.id}", json={"status": "draft"})
    assert response.status_code == 200
    assert response.json()["deleted_at"] is None


def test_patch_publish_sets_published_at(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"status": "publish"})
    assert response.status_code == 200
    assert response.json()["published_at"] is not None
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: FAIL (hoy `status` se asigna directo con `setattr`, sin motor ni trash lock).

- [ ] **Step 3: Conectar el trash lock y el motor de transición en `update_post`**

```python
from app.errors.exceptions import TrashPostLocked
from app.services.post_state import PostStateService

_state_service = PostStateService()


def _enforce_trash_lock(post: Post, incoming_fields: set[str]):
    if post.status == "trash" and incoming_fields - {"status"}:
        raise TrashPostLocked()


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

    db.commit()
    db.refresh(post)
    return post
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/posts.py tests/integration/test_update.py
git commit -m "feat: trash lock e integracion del motor de transicion en PATCH"
```

---

### Task 6: Reglas de preservación de `PUT` + slug al omitirse

**Files:**
- Modify: `app/routers/posts.py`
- Modify: `tests/integration/test_update.py`

- [ ] **Step 1: Agregar los tests que fallan**

```python
def test_put_without_status_preserves_it(client, db_session):
    post = _seed_post(db_session)
    client.patch(f"/posts/{post.id}", json={"status": "publish"})
    response = client.put(f"/posts/{post.id}", json={"title": "T2", "content": "C2"})
    assert response.json()["status"] == "publish"


def test_put_without_author_id_preserves_it(client, db_session):
    post = _seed_post(db_session)
    response = client.put(f"/posts/{post.id}", json={"title": "T2", "content": "C2"})
    assert response.json()["author_id"] == post.author_id


def test_put_without_slug_regenerates_it(client, db_session):
    post = _seed_post(db_session, slug="original")
    response = client.put(
        f"/posts/{post.id}", json={"title": "Nuevo Titulo", "content": "C2"}
    )
    assert response.json()["slug"] != "original"
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: FAIL (`replace_post` hoy resetea `status`/`author_id` a `None` cuando
se omiten, y no regenera `slug`).

- [ ] **Step 3: Implementar el helper de slug y reescribir `replace_post`**

```python
import re


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

    db.commit()
    db.refresh(post)
    return post
```

> Nota: el helper `_slugify` es una implementación mínima, privada a este
> router, solo para cubrir el caso de PUT sin `slug`. Cuando Store (Spec 3) se
> implemente y decida dónde vive la utilidad canónica de slugs (ej.
> `app/core/slug.py`), puede reemplazar este helper sin cambiar el contrato
> de Update.

- [ ] **Step 4: Correr y verificar que pasan**

Run: `python -m pytest tests/integration/test_update.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/posts.py tests/integration/test_update.py
git commit -m "feat: PUT preserva status/author_id y regenera slug al omitirse"
```

---

### Task 7: `updated_at` siempre bumpeado, contratos generales y suite E2E

**Files:**
- Modify: `app/routers/posts.py` (bump manual de `updated_at`)
- Modify: `tests/integration/test_update.py`
- Create: `tests/e2e/__init__.py`, `tests/e2e/test_update_e2e.py`

- [ ] **Step 1: Agregar los tests que fallan**

Agregar a `tests/integration/test_update.py`:

```python
from datetime import datetime

CANONICAL_FIELDS = {
    "id", "title", "content", "excerpt", "slug", "status", "author_id",
    "created_at", "updated_at", "published_at", "deleted_at",
}


def test_patch_noop_status_bumps_updated_at(client, db_session):
    post = _seed_post(db_session)
    original_updated_at = post.updated_at
    response = client.patch(f"/posts/{post.id}", json={"status": "draft"})
    assert response.status_code == 200
    new_updated_at = datetime.fromisoformat(response.json()["updated_at"])
    assert new_updated_at >= original_updated_at


def test_response_has_exactly_11_fields(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(f"/posts/{post.id}", json={"title": "x"})
    assert set(response.json().keys()) == CANONICAL_FIELDS


def test_id_and_created_at_are_immutable(client, db_session):
    post = _seed_post(db_session)
    response = client.patch(
        f"/posts/{post.id}", json={"id": 9999, "created_at": "2000-01-01T00:00:00"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == post.id
```

`tests/e2e/__init__.py` vacío. `tests/e2e/test_update_e2e.py`:

```python
def test_full_post_lifecycle(client, db_session):
    from tests.integration.test_update import _seed_post

    post = _seed_post(db_session)

    r1 = client.patch(f"/posts/{post.id}", json={"title": "Editado"})
    assert r1.status_code == 200

    r2 = client.put(f"/posts/{post.id}", json={"title": "Reemplazado", "content": "Nuevo"})
    assert r2.status_code == 200

    r3 = client.patch(f"/posts/{post.id}", json={"status": "publish"})
    assert r3.status_code == 200
    assert r3.json()["published_at"] is not None

    r4 = client.patch(f"/posts/{post.id}", json={"status": "trash"})
    assert r4.status_code == 200
    assert r4.json()["deleted_at"] is not None

    r5 = client.patch(f"/posts/{post.id}", json={"title": "no permitido"})
    assert r5.status_code == 422

    r6 = client.patch(f"/posts/{post.id}", json={"status": "draft"})
    assert r6.status_code == 200
    assert r6.json()["deleted_at"] is None
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python -m pytest tests/integration/test_update.py tests/e2e/ -v`
Expected: FAIL (`updated_at` no se reasigna en no-ops; `id`/`created_at` no
están protegidos explícitamente todavía, aunque `PostUpdate` no los declara).

- [ ] **Step 3: Bumpear `updated_at` a mano antes de cada commit**

En ambos handlers (`update_post` y `replace_post`), justo antes de `db.commit()`:

```python
from datetime import datetime, timezone

post.updated_at = datetime.now(timezone.utc)
db.commit()
db.refresh(post)
return post
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `python -m pytest tests/integration/test_update.py tests/e2e/ -v`
Expected: PASS.

- [ ] **Step 5: Correr la suite completa (todo verde)**

Run: `python -m pytest -v`
Expected: PASS en todos los tests, incluidos los de Spec 0.

---

## Definition of Done (Spec 4)

- [ ] Suite completa verde: `python -m pytest -v`
- [ ] `PostStateService` implementado, sin cambios de firma respecto a Spec 0
- [ ] `PATCH`/`PUT /posts/{id}` cubren los 8 pasos de precedencia del spec
- [ ] Trash lock y transición de estado devuelven los códigos `422` correctos
- [ ] `updated_at` cambia en toda respuesta `200`, incluidos no-ops
- [ ] Respuesta siempre con los 11 campos canónicos de `PostRead`
- [ ] Colección Postman corriendo en verde (Newman o Postman Runner)
- [ ] Todos los commits en `spec-4-melisa`, tests de las demás specs siguen en verde
