# Spec 2 — Show (`GET /posts/{id}`)

**Persona:** P3 · **Endpoint:** `GET /posts/{id}`
**Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Pytest
**Base:** `main` (Spec 0 congelada) · **Branch:** `spec-2-ale`

> Diseño extendido:
> [`docs/superpowers/specs/2026-07-06-spec-2-show-design.md`](../../../docs/superpowers/specs/2026-07-06-spec-2-show-design.md)
> · Plan TDD:
> [`docs/superpowers/plans/2026-07-06-spec-2-show.md`](../../../docs/superpowers/plans/2026-07-06-spec-2-show.md)

## Objetivo

Implementar `GET /posts/{id}` para devolver un post individual con el contrato JSON
canónico definido en Spec 0. La lectura debe respetar el formato estándar de errores
del equipo: si el post no existe o si está en `trash`, la respuesta es `404` con
`POST_NOT_FOUND`.

## Alcance

- `GET /posts/{id}` devuelve `200` con el post cuando existe y no está en `trash`.
- `GET /posts/{id}` devuelve `404` con el error estándar y `code: "POST_NOT_FOUND"`
  cuando el id no existe.
- `GET /posts/{id}` devuelve `404` con el error estándar y `code: "POST_NOT_FOUND"`
  cuando el post existe pero su estado es `trash`.
- La respuesta exitosa conserva exactamente los 11 campos del contrato canónico de Post,
  sin wrappers ni campos extra.

## Fuera de alcance

- Control de acceso por estado `private`.
- Lógica de transición de estados.
- Listados, filtros o paginación.
- Cambios al contrato JSON canónico o al formato estándar de error.

## Criterios de aceptación

1. Dado un post existente con id válido y estado distinto de `trash`, cuando hago
	`GET /posts/{id}`, entonces recibo `200` y el post con los mismos campos del
	contrato canónico, sin wrapper extra.
2. Dado un id inexistente, cuando hago `GET /posts/{id}`, entonces recibo `404` con
	el formato estándar de error, `code: "POST_NOT_FOUND"`, y el resto de campos
	acordados por el equipo.
3. Dado un post en estado `trash`, cuando hago `GET /posts/{id}`, entonces recibo
	`404` con el formato estándar de error, `code: "POST_NOT_FOUND"`, y sin exponer
	el recurso.
4. Los casos de éxito y error deben estar cubiertos por tests automatizados.

## Salidas de Spec 2

- [ ] `GET /posts/{id}` con `200` y contrato canónico cuando el post existe.
- [ ] `GET /posts/{id}` con `404 POST_NOT_FOUND` cuando el id no existe.
- [ ] `GET /posts/{id}` con `404 POST_NOT_FOUND` cuando el post está en `trash`.
- [ ] Tests automatizados cubriendo caso feliz y casos de error.
- [ ] Este documento y `docs/superpowers/plans/2026-07-06-spec-2-show.md`.