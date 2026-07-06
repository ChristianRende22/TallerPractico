# CMS Posts API — Taller Práctico

API REST para la gestión de _posts_ de un CMS, construida como **taller de equipo**
del Ciclo 8 (Patrones). El trabajo se dividió en **6 specs** (una fundación + un
endpoint del CRUD por persona), integradas todas en `main`.

Ofrece el CRUD completo de posts con paginación, búsqueda, filtros, ordenamiento,
máquina de estados (draft → publish → trash…), _soft delete_ / _hard delete_ y un
formato de error uniforme.

---

## Stack

- **Python 3.12**
- **FastAPI** — framework web / routing
- **SQLAlchemy 2.0** — ORM
- **Alembic** — migraciones + seed inicial de usuarios
- **Pydantic v2** — validación y schemas de request/response
- **Pytest** — tests (unit, integración, e2e)
- **SQLite** — base de datos (`posts.db`)
- **Postman / Newman** — colecciones de prueba end-to-end

---

## Estructura del proyecto

```
app/
  main.py                 # create_app() + registro de routers y error handlers
  database.py             # engine, SessionLocal, Base, get_db()
  models/                 # User, Post (+ POST_STATUSES)
  schemas/                # Pydantic: PostCreate/Read/List/Update/Replace, Pagination
  routers/
    health.py            # GET /health
    posts.py             # index, show, create, update, replace, delete
  services/
    post_query.py        # list_posts() — paginación/search/filtros/orden
    post_state.py        # PostStateService — máquina de estados
  errors/                 # AppError + subclases, handlers → contrato JSON
alembic/                  # migración 0001 (schema + seed de usuarios Ana/Luis)
postman/                  # 5 colecciones CMS-Posts-SpecN-*.json + seeds
tests/                    # unit/ integration/ e2e/ + tests de foundation
docs/ , doc/              # specs de diseño y planes TDD por cada spec
```

---

## Puesta en marcha

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear la base de datos (schema + seed de usuarios Ana id=1, Luis id=2)
python -m alembic upgrade head

# 3. Levantar la API
python -m uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000`. Documentación interactiva en
`http://127.0.0.1:8000/docs`.

---

## Endpoints

| Método   | Ruta               | Descripción                                                       |
|----------|--------------------|-------------------------------------------------------------------|
| `GET`    | `/health`          | Health check (`{"status": "ok"}`)                                 |
| `GET`    | `/posts`           | Listado con paginación, búsqueda, filtros y orden                 |
| `GET`    | `/posts/{id}`      | Detalle de un post (los que están en `trash` devuelven 404)       |
| `POST`   | `/posts`           | Crear post (genera `slug` automáticamente)                        |
| `PATCH`  | `/posts/{id}`      | Actualización **parcial** (solo los campos enviados)              |
| `PUT`    | `/posts/{id}`      | Reemplazo **completo** del post                                   |
| `DELETE` | `/posts/{id}`      | _Soft delete_ → `status=trash` (200)                              |
| `DELETE` | `/posts/{id}?force=true` | _Hard delete_ → elimina el registro (204, sin body)         |

### Parámetros de `GET /posts`

| Query      | Default        | Notas                                                       |
|------------|----------------|-------------------------------------------------------------|
| `page`     | `1`            | ≥ 1                                                         |
| `per_page` | `10`           | 1–100                                                      |
| `search`   | —              | Busca en título y contenido                                 |
| `status`   | —              | Uno de los estados válidos                                  |
| `author`   | —              | `author_id`                                                |
| `orderby`  | `created_at`   | Campo ordenable                                            |
| `order`    | `desc`         | `asc` \| `desc`                                            |

Respuesta paginada: `{ "data": [...], "pagination": { total, page, per_page, total_pages } }`.

---

## Modelo de datos

**Post** (11 campos canónicos que devuelve `PostRead`):

`id`, `title`, `content`, `excerpt`, `slug`, `status`, `author_id`,
`created_at`, `updated_at`, `published_at`, `deleted_at`.

**Estados válidos** (`POST_STATUSES`): `draft`, `pending`, `publish`, `private`, `trash`.

**Máquina de estados** (`PostStateService`):
- Pasar a `publish` exige `title` y `content` no vacíos; setea `published_at` la
  primera vez (idempotente en publicaciones posteriores).
- Pasar a `trash` setea `deleted_at` (_soft delete_); salir de `trash` lo limpia.
- Un post en `trash` está **bloqueado**: solo se acepta cambiar su `status`
  (restaurarlo); editar cualquier otro campo devuelve `422 TRASH_POST_LOCKED`.

---

## Formato de error

Todas las respuestas de error siguen el mismo contrato (definido en Spec 0):

```json
{ "error": "Post not found", "code": "POST_NOT_FOUND", "status": 404 }
```

Los errores de validación agregan `details: [{ field, message }]`.

| Código                      | HTTP | Cuándo                                             |
|-----------------------------|------|----------------------------------------------------|
| `VALIDATION_ERROR`          | 400  | Body/query inválido                                |
| `POST_NOT_FOUND`            | 404  | Post inexistente o en `trash` (en show)            |
| `INVALID_STATUS_TRANSITION` | 422  | Transición de estado no permitida                  |
| `TRASH_POST_LOCKED`         | 422  | Editar un campo de un post en `trash`              |
| `INTERNAL_ERROR`            | 500  | Error no controlado                                |

> **Nota de contrato:** los errores sin detalle (p. ej. `POST_NOT_FOUND`) **no**
> incluyen la clave `details`. Es parte del contrato canónico de Spec 0.

---

## Tests

```bash
python -m pytest -q      # 90 tests (unit + integración + e2e)
```

---

## Colecciones Postman

En `postman/` hay una colección por spec, con el patrón `CMS Posts - Spec N`:

| Archivo                                     | Cubre               |
|---------------------------------------------|---------------------|
| `CMS-Posts-Spec1-Index.postman_collection.json`  | `GET /posts`        |
| `CMS-Posts-Spec2-Show.postman_collection.json`   | `GET /posts/{id}`   |
| `CMS-Posts-Spec3-Create.postman_collection.json` | `POST /posts`       |
| `CMS-Posts-Spec4-Update.postman_collection.json` | `PATCH` / `PUT`     |
| `CMS-Posts-Spec5-Delete.postman_collection.json` | `DELETE`            |

`baseUrl` ya apunta a `http://127.0.0.1:8000`.

### Seeds

Cada colección espera un estado de BD específico. Antes de correrla, sembrá los
datos que necesita (los seeds hacen `DELETE` + `INSERT`, así los ids quedan estables):

- `python postman/seed_show_data.py` → **Spec 2 y Spec 5** (post id=1 normal, id=2 en trash)
- `python postman/seed_demo_data.py` → **Spec 1 y Spec 4** (ids 1–20 en estados exactos)
- **Spec 3** es autónoma (crea sus propios posts).

### Correr con Newman (CLI)

```bash
# con la API levantada en otra terminal:
python postman/seed_demo_data.py
npx newman run "postman/CMS-Posts-Spec4-Update.postman_collection.json"
```

**Última verificación (todas verdes):**

| Colección    | Requests | Assertions | Resultado |
|--------------|----------|------------|-----------|
| Spec 1 Index | 11       | 23         | ✅        |
| Spec 2 Show  | 3        | 13         | ✅        |
| Spec 3 Create| 5        | 0*         | ✅ (ejecuta) |
| Spec 4 Update| 25       | 50         | ✅        |
| Spec 5 Delete| 6        | 16         | ✅        |

\* La colección de Spec 3 ejecuta sus requests correctamente (201 al crear, 400 en
validación) pero todavía no tiene _test scripts_ que hagan assertions.

---

## Convenciones del equipo

- **Fundación (Spec 0) congelada:** `app/database.py`, `app/models/`, `app/errors/`,
  `app/routers/health.py`. Cada spec de endpoint solo toca `app/routers/posts.py`,
  `app/schemas/`, `tests/` y sus propios `app/services/`.
- Cada spec tiene doc autocontenido en `doc/ai/plans/0X-*.md` y diseño/plan extendidos
  en `docs/superpowers/`.
- Flujo por spec: rama `feat/spec-N-*` desde `main` → TDD → commit por tarea con tests
  verdes → merge a `main`.

| Spec | Endpoint            | Estado |
|------|---------------------|--------|
| 0    | Foundation          | ✅ en `main` |
| 1    | `GET /posts` (index)| ✅ en `main` |
| 2    | `GET /posts/{id}`   | ✅ en `main` |
| 3    | `POST /posts`       | ✅ en `main` |
| 4    | `PATCH` / `PUT`     | ✅ en `main` |
| 5    | `DELETE`            | ✅ en `main` |
