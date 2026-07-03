# Spec 0 — Foundation

**Persona:** P1 · **Endpoint:** Setup + modelo + errores + health check
**Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + Pytest
**Estado:** ✅ Completada e integrada en `main` (13 tests en verde)

> Documento de diseño extendido (con estructura de carpetas y notas de
> implementación):
> [`docs/superpowers/specs/2026-07-03-spec-0-foundation-design.md`](../../../docs/superpowers/specs/2026-07-03-spec-0-foundation-design.md)
> · Plan TDD paso a paso:
> [`docs/superpowers/plans/2026-07-03-spec-0-foundation.md`](../../../docs/superpowers/plans/2026-07-03-spec-0-foundation.md)

---

## Objetivo

Establecer los cimientos compartidos por las 5 specs siguientes: schema de base
de datos, contrato JSON canónico de Post, formato estándar de errores, ruteo base
y health check. **Ninguna otra spec debe redefinir estos contratos.** Tras Spec 0
la fundación queda congelada: P2–P6 solo tocan `app/routers/posts.py`, sus
`app/schemas/` y sus `tests/`.

## Alcance

### 1. Modelo de datos

**Tabla `posts`**

| Campo | Tipo | Constraint |
|---|---|---|
| id | integer | PK, autoincrement |
| title | string | not null |
| content | text | not null |
| excerpt | string | nullable |
| slug | string | not null, unique |
| status | enum(draft, pending, publish, private, trash) | not null, default: draft |
| author_id | integer | FK → users.id, nullable, ON DELETE RESTRICT |
| created_at | datetime | not null, default now |
| updated_at | datetime | not null, default now |
| published_at | datetime | nullable |
| deleted_at | datetime | nullable |

**Tabla `users`** (mínima, da integridad real a `author_id`; auth fuera de alcance)

| Campo | Tipo | Constraint |
|---|---|---|
| id | integer | PK, autoincrement |
| name | string | not null |
| email | string | not null, unique |

**Estados válidos** (fuente única de verdad: `POST_STATUSES` en `app/models/post.py`):
`draft`, `pending`, `publish`, `private`, `trash`.

**Seed:** 2 usuarios (`id:1 "Ana"`, `id:2 "Luis"`) para que Spec 1 (filtro `author`)
y Spec 3 (Store con `author_id`) tengan datos reales contra qué testear.

### 2. Contrato JSON canónico de Post

Todos los endpoints devuelven exactamente esta forma (11 campos), sin wrappers propios.
Se materializa como el schema `PostRead` en `app/schemas/post.py`.

```json
{
  "id": 1,
  "title": "Mi primer post",
  "content": "Contenido...",
  "excerpt": "Resumen...",
  "slug": "mi-primer-post",
  "status": "draft",
  "author_id": 1,
  "created_at": "2026-07-03T10:30:00Z",
  "updated_at": "2026-07-03T10:30:00Z",
  "published_at": null,
  "deleted_at": null
}
```

### 3. Formato estándar de error

Un solo lugar produce el formato (`app/errors/handlers.py`); las specs solo lanzan
excepciones de `app/errors/exceptions.py`. Nadie arma JSON de error a mano.

```json
{
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "status": 400,
  "details": [
    { "field": "title", "message": "Title is required" }
  ]
}
```

| Código | Status | Excepción |
|---|---|---|
| `VALIDATION_ERROR` | 400 | `ValidationError` |
| `POST_NOT_FOUND` | 404 | `PostNotFound` |
| `INVALID_STATUS_TRANSITION` | 422 | `InvalidStatusTransition` |
| `TRASH_POST_LOCKED` | 422 | `TrashPostLocked` |
| `INTERNAL_ERROR` | 500 | (cualquier `Exception` no controlada) |

**Regla de contrato:** los errores de validación de body son **400**
`VALIDATION_ERROR`. El `422` nativo de FastAPI/Pydantic se intercepta y traduce a
este formato; el `422` queda reservado a reglas de negocio.

### 4. Health check

`GET /health` → `200 {"status": "ok"}`.

### 5. Interfaz de `PostStateService` (contrato; implementación: Spec 4 / P5)

Publicada como **stub** en `app/services/post_state.py` (lanza `NotImplementedError`),
para que P6 (Delete) codee contra la interfaz desde el día 1. La lógica NO es de Spec 0.

```
PostStateService
├── can_transition(post, new_status) -> bool
├── transition(post, new_status) -> Post
│     ├── draft/pending/private → publish: exige title y content no vacíos,
│     │                            setea published_at solo la primera vez
│     ├── cualquiera → trash: setea deleted_at
│     └── trash → otro: limpia deleted_at (restauración)
└── Regla dura: post en trash no acepta update de campos → 422 TRASH_POST_LOCKED
```

## Criterios de aceptación (Given/When/Then)

- *Given* la BD está migrada, *When* se hace `GET /health`, *Then* responde
  `200 {"status":"ok"}`.
- *Given* existen 2 usuarios sembrados, *When* se consulta `users`, *Then* ambos
  existen con id, name, email.
- *Given* un post con `author_id` inválido (no existe en users), *When* se intenta
  insertar, *Then* la FK lo rechaza a nivel de BD.
- *Given* cualquier endpoint lanza un error de validación, *When* se serializa,
  *Then* cumple exactamente el formato estándar (mismos 4 campos, mismos nombres).
- *Given* cualquier endpoint devuelve un post, *When* se serializa, *Then* contiene
  exactamente los 11 campos del contrato, sin extras ni faltantes.

## Fuera de alcance

- ❌ Autenticación y autorización (login, tokens, permisos por rol)
- ❌ CRUD de usuarios vía API
- ❌ Relaciones adicionales (comentarios, categorías, tags)
- ❌ Lógica de transiciones implementada (solo se publica la interfaz; impl. = Spec 4)

## Salidas de Spec 0 (Definition of Done) — ✅ cumplidas

- [x] Migración `users` (id, name, email) + seed de 2 registros → `alembic/versions/0001_initial.py`
- [x] Migración `posts` con FK a users → mismo archivo
- [x] Capa de BD (`engine`/`session`/`get_db`) → `app/database.py`
- [x] Modelos `User` y `Post` + `POST_STATUSES` → `app/models/`
- [x] Schemas `PostRead` + `Pagination` → `app/schemas/post.py`
- [x] Router base `/posts` (vacío) montado → `app/routers/posts.py`
- [x] `GET /health` con test pasando → `app/routers/health.py`, `tests/test_health.py`
- [x] Handler global de errores + traducción Pydantic → 400 → `app/errors/`
- [x] `conftest.py` con fixtures compartidas → `tests/conftest.py`
- [x] Interfaz `PostStateService` (stub) → `app/services/post_state.py`

## Mapa de archivos (referencia rápida para P2–P6)

```
app/
├── main.py               create_app(): monta routers y error handlers
├── database.py           engine, SessionLocal, Base, get_db()  [FROZEN]
├── models/
│   ├── user.py           User                                  [FROZEN]
│   └── post.py           Post + POST_STATUSES                  [FROZEN]
├── schemas/
│   └── post.py           PostRead (contrato), Pagination       [extender aquí]
├── routers/
│   ├── health.py         GET /health                           [FROZEN]
│   └── posts.py          router /posts vacío                   [P2–P6 trabajan aquí]
├── errors/
│   ├── exceptions.py     AppError + subclases                  [FROZEN]
│   └── handlers.py       formato JSON estándar                 [FROZEN]
└── services/
    └── post_state.py     PostStateService (stub)               [P5 implementa]
alembic/versions/0001_initial.py   schema + seed
tests/conftest.py                  fixtures compartidas          [heredar]
```

## Cómo levantar y verificar

```bash
python -m pip install -r requirements.txt
python -m pytest -v                       # 13 tests en verde
python -m alembic upgrade head            # crea posts.db con schema + seed
python -m uvicorn app.main:app --reload   # API en http://127.0.0.1:8000
#   GET http://127.0.0.1:8000/health   -> {"status":"ok"}
#   Docs interactivas: /docs
```

## Cómo arranca cada persona su spec

```bash
git checkout main && git pull
git checkout -b feat/spec-1-index main    # (ajustar número/nombre)
# trabajar solo en routers/posts.py, schemas/, tests/  · TDD · commit por tarea · PR a main
```
