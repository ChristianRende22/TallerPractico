# Spec 0 — Foundation (diseño)

**Stack:** FastAPI + SQLAlchemy + Alembic + Pytest
**Branch:** `feat/spec-0-foundation`
**Fecha:** 2026-07-03

## Objetivo

Establecer los cimientos compartidos por las 5 specs siguientes: schema de base
de datos, contrato JSON canónico de Post, formato estándar de errores, ruteo base
y health check. Ninguna otra spec debe redefinir estos contratos. Tras Spec 0, la
fundación (models, database, errors, health, fixtures) queda **congelada**.

## Arquitectura y estructura de carpetas

Capas explícitas para que cada spec siguiente tenga un lugar obvio sin pisarse.
P2–P6 solo tocan `routers/posts.py`, sus `schemas/` y sus `tests/`.

```
app/
├── main.py                 # crea la app FastAPI, monta routers y error handlers
├── database.py             # engine, SessionLocal, Base, get_db() (dependency)
├── models/
│   ├── user.py             # modelo User
│   └── post.py             # modelo Post + constante POST_STATUSES
├── schemas/
│   └── post.py             # PostRead (forma JSON canónica) + Pagination
├── routers/
│   ├── health.py           # GET /health          (Spec 0)
│   └── posts.py            # router montado en /posts, vacío (lo llenan P2–P6)
├── errors/
│   ├── exceptions.py       # AppError + subclases
│   └── handlers.py         # handlers globales → formato JSON estándar
├── services/
│   └── post_state.py       # PostStateService: solo interfaz/contrato (impl. = Spec 4)
└── core/
    └── slug.py             # stub declarado, lo implementa Store (Spec 3)
alembic/                    # migraciones
tests/
├── conftest.py             # fixtures: app, client, db de test (SQLite en memoria)
├── test_health.py
└── test_error_format.py
```

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
| author_id | integer | FK → users.id, nullable |
| created_at | datetime | not null |
| updated_at | datetime | not null |
| published_at | datetime | nullable |
| deleted_at | datetime | nullable |

**Tabla `users`** (mínima, da integridad real a `author_id`; auth fuera de alcance)

| Campo | Tipo | Constraint |
|---|---|---|
| id | integer | PK, autoincrement |
| name | string | not null |
| email | string | not null, unique |

**FK `posts.author_id → users.id`:** nullable, `ON DELETE RESTRICT`. Como no hay
endpoint para borrar usuarios, RESTRICT nunca se dispara en la práctica pero deja
la integridad protegida. La FK rechaza valores no-null inexistentes.

**Enum `status`:** `draft`, `pending`, `publish`, `private`, `trash`. Se expone
como constante compartida `POST_STATUSES` en `models/post.py` para que P4
(transiciones) y P5 (delete) importen la misma verdad y nadie escriba el string a mano.

**Seed:** 2 usuarios (ej. `id:1 "Ana"`, `id:2 "Luis"`) para que Spec 1 (filtro
`author`) y Spec 3 (Store con `author_id`) tengan datos reales contra qué testear.

### 2. Contrato JSON canónico de Post

Todos los endpoints devuelven exactamente esta forma (11 campos), sin wrappers propios:

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

Se materializa como el schema Pydantic `PostRead` en `schemas/post.py`.

### 3. Formato estándar de error

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

Códigos: `VALIDATION_ERROR` (400), `POST_NOT_FOUND` (404),
`INVALID_STATUS_TRANSITION` (422), `TRASH_POST_LOCKED` (422), `INTERNAL_ERROR` (500).

**Jerarquía de excepciones** (`errors/exceptions.py`):

```
AppError(status, code, message, details=None)   # base
├── ValidationError          → 400  VALIDATION_ERROR   (details: [{field, message}])
├── PostNotFound             → 404  POST_NOT_FOUND
├── InvalidStatusTransition  → 422  INVALID_STATUS_TRANSITION
└── TrashPostLocked          → 422  TRASH_POST_LOCKED
```

**Handlers globales** (`errors/handlers.py`, registrados en `main.py`):

- `AppError` → serializa al contrato exacto (4 campos + `details` opcional).
- Cualquier `Exception` no controlada → `500 INTERNAL_ERROR`, sin filtrar stacktrace.
- **Puente con FastAPI:** el `RequestValidationError` nativo de Pydantic (422, formato
  propio) se **intercepta y traduce** a `VALIDATION_ERROR` (400, `details:
  [{field, message}]`). Decisión de contrato: los errores de validación de body son
  **400**; el **422** queda reservado a reglas de negocio
  (`INVALID_STATUS_TRANSITION`, `TRASH_POST_LOCKED`). Este es el único punto donde se
  sobreescribe el default de FastAPI, y es lo que mantiene un solo formato de error.

### 4. Health check

`GET /health` → `200 {"status": "ok"}`. Es el primer test verde y sirve de humo:
si pasa, la app monta bien.

### 5. Interfaz de `PostStateService` (contrato; dueño de implementación: P5/Spec 4)

Se publica **solo la interfaz** (firma + docstring de reglas) lanzando
`NotImplementedError`, para que P6 (Delete) pueda codear contra ella desde el día 1.
La lógica NO es de Spec 0.

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

## Estrategia de tests

- `pytest` + `TestClient` (httpx).
- `conftest.py` provee fixtures compartidas: BD **SQLite en memoria** por test
  (rápida, aislada), `client`, y override de `get_db()`. Cada test arranca con
  schema limpio. P2–P6 heredan estas fixtures y solo escriben sus asserts —
  evita que cada persona invente su propio setup de BD.

## Criterios de aceptación (Given/When/Then)

- *Given* la BD está migrada, *When* se hace `GET /health`, *Then* responde
  `200 {"status":"ok"}`.
- *Given* existen 2 usuarios sembrados, *When* se consulta la tabla `users`,
  *Then* ambos existen con id, name, email.
- *Given* un post con `author_id` inválido (no existe en users), *When* se intenta
  insertar, *Then* la FK rechaza la operación a nivel de BD.
- *Given* cualquier endpoint lanza un error de validación, *When* se serializa la
  respuesta, *Then* cumple exactamente el formato estándar (mismos 4 campos, mismos
  nombres).
- *Given* cualquier endpoint devuelve un post, *When* se serializa, *Then* contiene
  exactamente los 11 campos del contrato canónico, sin campos extra ni faltantes.

## Fuera de alcance

- ❌ Autenticación y autorización (login, tokens, permisos por rol)
- ❌ CRUD de usuarios (crear/editar/borrar users vía API)
- ❌ Relaciones adicionales (comentarios, categorías, tags)
- ❌ Lógica de transiciones de estado implementada (solo se publica la interfaz;
  la implementación es Spec 4)

## Salidas de Spec 0 (Definition of Done)

- [ ] Migración `users` (id, name, email) + seed de 2 registros
- [ ] Migración `posts` con FK a users
- [ ] `database.py` (engine/session/`get_db()`)
- [ ] Modelos `User` y `Post` + constante `POST_STATUSES`
- [ ] Schema Pydantic `PostRead` + `Pagination`
- [ ] Router base `/posts` (vacío) montado
- [ ] `GET /health` con test pasando
- [ ] Handler global de errores + traducción Pydantic → 400
- [ ] `conftest.py` con fixtures compartidas
- [ ] Interfaz `PostStateService` (stub con contrato)
- [ ] Este documento y `doc/ai/plans/00-foundation.md`
