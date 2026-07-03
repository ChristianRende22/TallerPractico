# Spec 1 — Index (`GET /posts`)

**Persona:** P2 · **Endpoint:** `GET /posts`
**Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Pytest
**Base:** `main` (Spec 0 congelada) · **Branch:** `feat/spec-1-index`

> Diseño extendido:
> [`docs/superpowers/specs/2026-07-03-spec-1-index-design.md`](../../../docs/superpowers/specs/2026-07-03-spec-1-index-design.md)
> · Plan TDD:
> [`docs/superpowers/plans/2026-07-03-spec-1-index.md`](../../../docs/superpowers/plans/2026-07-03-spec-1-index.md)

## Objetivo

Listar posts con paginación, búsqueda, filtros y ordenamiento vía `GET /posts`,
devolviendo la respuesta paginada acordada en Spec 0. Reusa `PostRead`, el formato
de error y `get_db` de la fundación; no redefine contratos.

## Query params

| Param | Tipo | Default | Regla |
|---|---|---|---|
| `page` | int | 1 | ≥ 1 |
| `per_page` | int | 10 | 1–100 |
| `search` | str | — | substring case-insensitive en `title` + `content` |
| `status` | str | — | uno de `POST_STATUSES`; por defecto excluye `trash`; `status=trash` trae trash |
| `author` | int | — | `author_id` exacto |
| `orderby` | str | `created_at` | whitelist: `created_at`, `updated_at`, `title`, `id` |
| `order` | str | `desc` | `asc` / `desc` |

## Reglas de negocio

- **Trash oculto por defecto:** sin `status` → `status != 'trash'`. Con `status`
  válido → filtra ese estado exacto (incluye `trash`).
- **Búsqueda:** `search=foo` → `title` o `content` contienen `foo` (case-insensitive).
- Filtros presentes se combinan con AND.
- **Paginación:** `total` = conteo con filtros; `total_pages = ceil(total/per_page)`;
  `offset = (page-1)*per_page`. Página fuera de rango → `data: []` sin error.

## Respuesta (200)

```json
{
  "data": [ { ...post (11 campos canónicos) } ],
  "pagination": { "total": 42, "page": 1, "per_page": 10, "total_pages": 5 }
}
```

## Errores → 400 `VALIDATION_ERROR` (formato estándar de Spec 0)

- `page<1`, `per_page<1`, `per_page>100`, tipos no numéricos → constraints de `Query`.
- `status` fuera de `POST_STATUSES`, `orderby` fuera de whitelist, `order` ≠ asc/desc
  → validación explícita que lanza `ValidationError`.

## Arquitectura

- `app/routers/posts.py` — `GET /posts` → `index()`: declara params, valida enums,
  delega y arma la respuesta (handler delgado).
- `app/services/post_query.py` (nuevo) — `list_posts(db, filters) -> (items, total)`:
  filtros/orden/paginación en un solo lugar, testeable sin HTTP.
- `app/schemas/post.py` — se agrega `PostList` (`data: list[PostRead]`, `pagination: Pagination`).

## Criterios de aceptación (resumen)

Paginación (10 por página, `page=2` trae el resto), trash oculto por defecto,
`status=trash` lo trae, `search` en title+content case-insensitive, `author` filtra
por id, `orderby=title&order=asc` ordena, params inválidos → 400, base vacía → `data:[]`.

## Fuera de alcance

- ❌ Filtros por rango de fechas · ❌ Full-text avanzado · ❌ Multi-status
  (`status=draft,pending`) · ❌ Cursor pagination

## Salidas de Spec 1

- [ ] `GET /posts` con los 7 query params y constraints
- [ ] `app/services/post_query.py` con `list_posts()`
- [ ] `PostList` en `app/schemas/post.py`
- [ ] Tests por criterio de aceptación; Spec 0 sigue verde
- [ ] Este documento
