# Spec 1 — Index (`GET /posts`) (diseño)

**Persona:** P2 · **Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Pytest
**Base:** `main` (Spec 0 congelada) · **Branch:** `feat/spec-1-index`
**Fecha:** 2026-07-03

## Objetivo

Listar posts con paginación, búsqueda, filtros y ordenamiento vía `GET /posts`,
devolviendo la respuesta paginada acordada en Spec 0. No redefine contratos: reusa
`PostRead`, el formato de error y `get_db` de la fundación.

## Alcance

### Query params

| Param | Tipo | Default | Regla |
|---|---|---|---|
| `page` | int | 1 | ≥ 1 |
| `per_page` | int | 10 | 1–100 |
| `search` | str | — | substring case-insensitive en `title` + `content` |
| `status` | str | — | uno de `POST_STATUSES`; por defecto **excluye `trash`**; con `status=trash` trae trash |
| `author` | int | — | filtra por `author_id` exacto |
| `orderby` | str | `created_at` | whitelist: `created_at`, `updated_at`, `title`, `id` |
| `order` | str | `desc` | `asc` / `desc` |

### Reglas de negocio

- **Trash oculto por defecto:** si `status` no viene, la query filtra
  `status != 'trash'`. Si `status` viene con un valor válido (incluido `trash`),
  filtra por ese estado exacto.
- **Búsqueda:** `search=foo` → `WHERE (title ILIKE '%foo%' OR content ILIKE '%foo%')`.
  En SQLite se usa `LIKE` con `func.lower(...)` para case-insensitive.
- **Combinación:** todos los filtros presentes se aplican con AND.
- **Paginación:** `total` = conteo con los filtros aplicados (antes de offset/limit);
  `total_pages = ceil(total / per_page)`; `offset = (page - 1) * per_page`.
  Página fuera de rango devuelve `data: []` con el `pagination` correcto (no error).

### Respuesta (200)

```json
{
  "data": [ { ...post (11 campos canónicos) } ],
  "pagination": { "total": 42, "page": 1, "per_page": 10, "total_pages": 5 }
}
```

Cada elemento serializado con `PostRead`. El sobre lo aporta un schema nuevo
`PostList` (`data: list[PostRead]`, `pagination: Pagination`) en `app/schemas/post.py`.

### Errores

Cualquier parámetro inválido → **400 `VALIDATION_ERROR`** (formato estándar de Spec 0):

- `page < 1`, `per_page < 1`, `per_page > 100`, tipos no numéricos → validados por
  `Query(..., ge=..., le=...)` de FastAPI → traducidos a 400 por el handler global.
- `status` fuera de `POST_STATUSES`, `orderby` fuera de whitelist, `order` distinto
  de `asc`/`desc` → validación explícita en el endpoint que lanza `ValidationError`
  con `details: [{field, message}]`.

## Arquitectura

- **`app/routers/posts.py`** — agrega `@router.get("")` → `index()`. Declara los
  query params con sus constraints, delega la construcción de la query al servicio
  y arma la respuesta. Handler delgado.
- **`app/services/post_query.py`** (nuevo) — `list_posts(db, filters) -> (items, total)`.
  Contiene la lógica de filtros/orden/paginación en un solo lugar, testeable sin HTTP.
  Recibe un objeto/estructura simple de filtros ya validados.
- **`app/schemas/post.py`** — se agrega `PostList` (sobre paginado). `PostRead` y
  `Pagination` ya existen.

Flujo: `index()` valida enums → arma `filters` → `list_posts()` devuelve
`(items, total)` → `index()` calcula `total_pages` y devuelve `PostList`.

## Criterios de aceptación (Given/When/Then)

- *Given* 15 posts en `draft`, *When* `GET /posts`, *Then* devuelve 10 items,
  `pagination.total=15`, `total_pages=2`, `page=1`.
- *Given* 15 posts, *When* `GET /posts?page=2`, *Then* devuelve los 5 restantes.
- *Given* posts con distintos `status` incluyendo trash, *When* `GET /posts` sin
  `status`, *Then* NO aparece ningún post en `trash`.
- *Given* posts en trash, *When* `GET /posts?status=trash`, *Then* solo aparecen los
  de trash.
- *Given* posts con títulos variados, *When* `GET /posts?search=hola`, *Then* solo
  los que contienen "hola" en title o content (case-insensitive).
- *Given* posts de autores 1 y 2, *When* `GET /posts?author=1`, *Then* solo los del autor 1.
- *Given* posts con distintos `created_at`, *When* `GET /posts?orderby=title&order=asc`,
  *Then* vienen ordenados por título ascendente.
- *Given* cualquier request, *When* `GET /posts?per_page=999`, *Then* 400 `VALIDATION_ERROR`.
- *Given* cualquier request, *When* `GET /posts?status=xyz`, *Then* 400 `VALIDATION_ERROR`.
- *Given* cualquier request, *When* `GET /posts?orderby=hackme`, *Then* 400 `VALIDATION_ERROR`.
- *Given* base vacía, *When* `GET /posts`, *Then* `data: []`, `total=0`, `total_pages=0`.

## Fuera de alcance

- ❌ Filtros por rango de fechas
- ❌ Full-text search avanzado (ranking, stemming)
- ❌ Filtro multi-status (ej. `status=draft,pending`)
- ❌ Cursor pagination (solo offset/limit)

## Salidas de Spec 1

- [ ] `GET /posts` con los 7 query params y sus constraints
- [ ] `app/services/post_query.py` con `list_posts()`
- [ ] Schema `PostList` (sobre paginado) en `app/schemas/post.py`
- [ ] Tests cubriendo cada criterio de aceptación
- [ ] Tests de Spec 0 siguen en verde
- [ ] Este documento y `doc/ai/plans/01-index.md`
