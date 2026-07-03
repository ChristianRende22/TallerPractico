# Spec 0 — Foundation

> Documento de diseño canónico:
> [`docs/superpowers/specs/2026-07-03-spec-0-foundation-design.md`](../../../docs/superpowers/specs/2026-07-03-spec-0-foundation-design.md)
>
> Esta ruta existe para cumplir la convención del plan de equipo
> (`doc/ai/plans/0X-nombre.md`). El contenido completo —arquitectura, modelo de
> datos, contrato JSON, formato de error, interfaz de `PostStateService`,
> criterios de aceptación y Definition of Done— vive en el documento enlazado
> arriba para no duplicarse.

## Resumen

- **Stack:** FastAPI + SQLAlchemy + Alembic + Pytest
- **Entregable:** cimientos compartidos por las 5 specs siguientes (schema BD,
  contrato JSON canónico de Post, formato estándar de errores, ruteo base,
  `GET /health`, interfaz de `PostStateService`).
- **Regla:** tras Spec 0 la fundación queda congelada; ninguna otra spec
  redefine estos contratos.
