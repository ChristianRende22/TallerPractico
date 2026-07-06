# Spec 3 — Store

**Endpoint:** `POST /posts`
**Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Pytest
**Estado:** 📝 Planificación

---

## Objetivo

Implementar el endpoint para la creación de posts (`POST /posts`) asegurando la validación estricta de entrada, la asignación de valores por defecto requeridos y la integración con el contrato canónico establecido en la Spec 0.

## Alcance

### 1. Payload de Entrada (Schema `PostCreate`)

Se definirá el schema `PostCreate` en `app/schemas/post.py` para validar los datos de entrada en función de las reglas de negocio.

**Campos:**
- `title` (string): **Obligatorio**.
- `content` (string): **Obligatorio**.
- `status` (enum): Opcional. **Por defecto: `draft`** (si no se especifica en la petición).
- Otros campos (ej. `excerpt`, `author_id`, `slug`): Opcionales según el modelo base, pero no requeridos estrictamente para la creación básica. *Nota: dado que la BD exige que `slug` sea no nulo y único (según Spec 0), el sistema deberá autogenerarlo a partir del título si el usuario no lo provee.*

### 2. Validación de Entrada y Errores

El endpoint dependerá del handler global de excepciones configurado en Spec 0. Cualquier falla en la validación (p. ej., omitir `title` o enviar un tipo de dato incorrecto) generará automáticamente la respuesta estándar definida previamente:

```json
{
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "status": 400,
  "details": [
    { "field": "title", "message": "Field required" }
  ]
}
```

### 3. Salida

La respuesta exitosa será un código de estado `201 Created` y devolverá el JSON canónico `PostRead` (los 11 campos estipulados en Spec 0) sin wrappers de ningún tipo.

## Criterios de aceptación (Given/When/Then)

- *Given* un payload válido que contiene únicamente `title` y `content`, *When* se envía `POST /posts`, *Then* se crea el post, su status queda establecido como `draft`, y responde `201 Created` con el JSON canónico del post.
- *Given* un payload en el cual falta `title` o `content`, *When* se envía `POST /posts`, *Then* responde `400 VALIDATION_ERROR` detallando de forma clara los campos faltantes en formato JSON consistente.
- *Given* un payload que especifica explícitamente un `status` válido (p.ej. `publish`), *When* se envía `POST /posts`, *Then* el post se crea con el status especificado.
- *Given* la implementación completa, *When* se ejecuta la suite de tests (pytest), *Then* todos los nuevos tests de validación y creación del post pasan exitosamente (círculo verde).

## Plan de Implementación paso a paso (TDD)

1. **Definir Tests (Rojo):**
   - Crear/Editar el archivo de tests correspondiente (ej. `tests/test_posts_store.py`).
   - Escribir test: `test_create_post_success_minimal` (Valida retorno 201 y estado default `draft`).
   - Escribir test: `test_create_post_success_with_status` (Valida retorno 201 y override del estado).
   - Escribir test: `test_create_post_missing_title` (Valida retorno 400 y formato exacto del JSON de error `VALIDATION_ERROR`).
   - Escribir test: `test_create_post_missing_content` (Valida retorno 400 y error correspondiente).

2. **Implementar Schema:**
   - Agregar el schema `PostCreate` en `app/schemas/post.py` con las validaciones de Pydantic (`title` y `content` sin default para hacerlos obligatorios, `status` con default `PostStatus.DRAFT`).

3. **Implementar Router y Lógica (Verde):**
   - En `app/routers/posts.py`, definir el endpoint `@router.post("/", response_model=PostRead, status_code=status.HTTP_201_CREATED)`.
   - Implementar la lógica del manejador: instanciar el modelo de SQLAlchemy, generar `slug` de ser necesario (con slugify o equivalente), y ejecutar `db.add()`, `db.commit()`, `db.refresh()`.

4. **Refactor y Revisión:**
   - Asegurar que la implementación no redefine ninguna de las reglas congeladas en Spec 0 (rutas, errores, respuesta canónica).
   - Ejecutar la suite completa para confirmar que la creación y validación cumplen con todos los criterios de aceptación al 100%.
