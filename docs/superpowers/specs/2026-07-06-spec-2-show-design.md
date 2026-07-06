# Spec 2 — Show (`GET /posts/{id}`) (diseño)

**Persona:** P3 · **Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Pytest
**Base:** `main` (Spec 0 congelada) · **Branch:** `spec-2-ale`
**Fecha:** 2026-07-06

## Objetivo

Implementar la lectura de un post por id vía `GET /posts/{id}` respetando el contrato
canónico definido en Spec 0. El endpoint debe responder con el post serializado como
`PostRead` cuando existe y no está en `trash`, y debe responder `404` con
`POST_NOT_FOUND` cuando el id no existe o cuando el post está en `trash`.

## Alcance

### 1. Endpoint

| Método | Ruta | Respuesta | Regla |
|---|---|---|---|
| `GET` | `/posts/{id}` | `200` | Devuelve el post serializado con `PostRead` si existe y no está en `trash`. |
| `GET` | `/posts/{id}` | `404` | Devuelve el error estándar `POST_NOT_FOUND` si el id no existe. |
| `GET` | `/posts/{id}` | `404` | Devuelve el error estándar `POST_NOT_FOUND` si el post existe pero su estado es `trash`. |

### 2. Reglas de lectura

- La respuesta exitosa debe conservar exactamente los 11 campos del contrato canónico de
  Post, sin wrappers ni campos extra.
- Un post en `trash` no se expone por `GET /posts/{id}`; para esta spec se trata como
  inexistente.
- No se implementa control de acceso por estado `private`.
- No se implementa lógica de transición de estados en esta spec.

### 3. Errores

Cuando el post no existe o está en `trash`, el endpoint debe lanzar `PostNotFound` para
que el handler global de Spec 0 serialice la respuesta con el formato estándar del
proyecto.

```json
{
  "error": "Post not found",
  "code": "POST_NOT_FOUND",
  "status": 404,
  "details": []
}
```

No se debe construir el JSON de error manualmente dentro del router.

## Arquitectura

- **`app/routers/posts.py`** — agrega `@router.get("/{id}")` con un handler delgado que
  obtiene el post por id, valida la regla de `trash` y devuelve `PostRead`.
- **`app/schemas/post.py`** — no se modifica; `PostRead` ya define la forma canónica de
  salida.
- **`app/errors/exceptions.py`** — no se modifica; se reutiliza `PostNotFound`.
- **`tests/`** — se agregan tests de integración para el caso feliz, el id inexistente y
  el post en `trash`.

Flujo: `show()` consulta el post → si no existe o está en `trash`, lanza
`PostNotFound` → el handler global responde `404` estándar → si existe y no está en
`trash`, el endpoint devuelve el modelo serializado con `PostRead`.

## Criterios de aceptación (Given/When/Then)

- *Given* un post existente con id válido y estado distinto de `trash`, *When* se hace
  `GET /posts/{id}`, *Then* responde `200` con el post usando exactamente los 11 campos
  del contrato canónico.
- *Given* un id inexistente, *When* se hace `GET /posts/{id}`, *Then* responde `404`
  con `POST_NOT_FOUND` y el formato estándar de error.
- *Given* un post en estado `trash`, *When* se hace `GET /posts/{id}`, *Then* responde
  `404` con `POST_NOT_FOUND` y no expone el recurso.
- *Given* la suite completa, *When* se ejecutan los tests, *Then* los tests de Spec 0 y
  las demás specs siguen en verde.

## Fuera de alcance

- ❌ Control de acceso por estado `private`
- ❌ Lógica de transición de estados
- ❌ Listados, filtros o paginación
- ❌ Cambios al contrato JSON canónico o al formato estándar de error

## Salidas de Spec 2

- [ ] Endpoint `GET /posts/{id}` implementado en `app/routers/posts.py`.
- [ ] Tests de integración cubriendo éxito, id inexistente y `trash`.
- [ ] Respuesta exitosa con `PostRead` y error estándar `POST_NOT_FOUND` en los casos negativos.
- [ ] Spec 0 y las demás specs siguen en verde.
- [ ] Este documento y `doc/ai/plans/02-show.md`.