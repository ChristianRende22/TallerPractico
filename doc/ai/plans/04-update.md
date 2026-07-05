# Spec 4 — Update

> Plan de implementación TDD paso a paso:
> [`docs/superpowers/plans/2026-07-04-spec-4-update.md`](../../../docs/superpowers/plans/2026-07-04-spec-4-update.md)

**Persona:** P5 · **Endpoint:** `PATCH /posts/{id}` · `PUT /posts/{id}`
**Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + Pytest
**Estado:** 📝 Definida, pendiente de implementación
**Depende de:** Spec 0 (Foundation) — usa `Post`, `PostRead`, `AppError` y el stub de `PostStateService`
**Bloquea a:** Spec 5 (Delete) — consume `PostStateService` implementado aquí

---

## Objetivo

Implementar `PATCH` (actualización parcial) y `PUT` (reemplazo total) de un post, e
**implementar por completo `PostStateService`**, cuya interfaz ya fue publicada como
stub en Spec 0. Esta spec es la única fuente de verdad del motor de transiciones de
estado; Spec 5 solo lo consume, no lo reimplementa.

## Alcance

### 1. Endpoints

| Método | Ruta | Body | Semántica |
|---|---|---|---|
| `PATCH` | `/posts/{id}` | parcial — solo los campos que cambian | Actualización incremental |
| `PUT` | `/posts/{id}` | total — `title` y `content` obligatorios | Reemplazo completo |

Ambos devuelven `200` con el post serializado según el contrato de Spec 0
(`PostRead`, 11 campos, sin wrappers), o `404 POST_NOT_FOUND` si el `id` no existe.

> **Nota:** PUT es un reemplazo de *contenido*, no un reset completo de todo
> el recurso — `status` y `author_id` se preservan si se omiten (ver Decisión #2).

### 2. Campos aceptados en el body de entrada (`app/schemas/post.py`)

**PATCH — todos los campos son opcionales**

| Campo | Obligatorio/Opcional | Nota |
|---|---|---|
| `title` | Opcional | texto |
| `content` | Opcional | texto |
| `excerpt` | Opcional | texto |
| `slug` | Opcional | texto |
| `author_id` | Opcional | entero |
| `status` | Opcional | uno de los 5 estados válidos |

**PUT — `title` y `content` obligatorios, el resto opcional**

| Campo | Obligatorio/Opcional | Nota |
|---|---|---|
| `title` | Obligatorio | texto |
| `content` | Obligatorio | texto |
| `excerpt` | Opcional | texto |
| `slug` | Opcional | texto |
| `author_id` | Opcional | entero |
| `status` | Opcional | uno de los 5 estados válidos |

`id`, `created_at`, `updated_at`, `published_at`, `deleted_at` **nunca** son
campos aceptados en el body de entrada de ninguno de los dos schemas, así que
cualquier intento de enviarlos se ignora silenciosamente.

### 3. Motor de transiciones de estado (`app/services/post_state.py`)

Esta spec implementa por completo la lógica de transición de estados que
Spec 0 dejó pendiente como interfaz. El servicio cubre dos responsabilidades:
decidir si una transición de estado es válida, y aplicar esa transición
actualizando los campos correspondientes del post.

Reglas de negocio:

- Todos los estados (`draft`, `pending`, `publish`, `private`, `trash`) pueden
  alcanzar a cualquier otro estado, incluida la transición de un estado a sí
  mismo (no-op).
- La única transición que puede rechazarse es hacia `publish`, y solo cuando
  `title` o `content` quedarían vacíos en el estado resultante; en ese caso se
  rechaza con el error de transición inválida (`422 INVALID_STATUS_TRANSITION`).
- Al transicionar hacia `publish`: si el post nunca había sido publicado antes,
  se le asigna la hora actual como fecha de publicación. Si ya tenía una fecha
  de publicación de una vez anterior, esa fecha no se modifica.
- Al transicionar hacia `trash`: se registra la hora actual como fecha de
  borrado.
- Al salir de `trash` hacia cualquier otro estado: se limpia la fecha de
  borrado.
- Si el estado nuevo es igual al estado actual (incluido un post en `trash`
  que se mantiene en `trash`): es un no-op de estado, no se reasigna ni la
  fecha de borrado ni la de publicación.

Regla dura (se evalúa antes de aplicar cualquier otro cambio): si el post está
actualmente en `trash` y el body trae algún campo distinto de `status`, la
operación se rechaza por completo (`422 TRASH_POST_LOCKED`), sin aplicar ningún
cambio. Esto incluye el caso de intentar restaurar y editar en la misma
llamada (por ejemplo, mandar `status: draft` junto con un nuevo `title`): se
rechaza completo. Restaurar y editar requieren dos llamadas separadas.

> **Nota:** los errores de transición inválida y de post bloqueado en trash
> (ya definidos en `app/errors/exceptions.py`, Spec 0) no aceptan `details` en
> su constructor, a diferencia del error de validación general. Si en el
> futuro se necesita enriquecer estos errores con `details`, hay que extender
> esas clases primero.

### 4. Orden de validación (precedencia — determinístico, en este orden exacto)

1. **Existencia** — `id` no existe → `404 POST_NOT_FOUND` (corta aquí, nada más se evalúa)
2. **Shape del body** — tipos, enum de `status` inválido, JSON malformado → `400 VALIDATION_ERROR` (Pydantic)
3. **Campos requeridos / no vacíos**:
   - PUT: `title` y `content` faltantes o `""` → `400 VALIDATION_ERROR`
   - PATCH: si `title`, `content`, `excerpt` o `slug` vienen presentes pero como `""` → `400 VALIDATION_ERROR`
   - PATCH con body `{}` (sin ningún campo) → `400 VALIDATION_ERROR` ("At least one field must be provided")
4. **Integridad referencial** — `author_id` presente y no existe en `users` → `400 VALIDATION_ERROR`
5. **Unicidad de slug** — `slug` presente y ya usado por OTRO post → `400 VALIDATION_ERROR` (no autosufija como Store; ver Decisión #3)
6. **Trash lock** — post actual en `trash` y el body trae algo más que `status` → `422 TRASH_POST_LOCKED`
7. **Transición de estado** — si `status` viene en el body y difiere del actual, se ejecuta la lógica de transición del motor de estados (ver sección 3):
   - falla la regla de publish (title/content vacíos) → `422 INVALID_STATUS_TRANSITION`
8. **Aplicación** — se escriben los campos, `updated_at = now()`, se persiste, se devuelve `200`.

> El paso 7 (falla de publish por campos vacíos) es hoy **defensivo**: dado que
> Store (Spec 3) y este mismo Update nunca permiten persistir `title`/`content`
> vacíos (paso 3 los bloquea antes), no hay forma de llegar a esa rama vía HTTP
> en el estado actual del dominio. Se implementa igual porque (a) es el contrato
> publicado en Spec 0/el documento maestro, y (b) blinda el sistema si en el
> futuro `content` se vuelve opcional. Se cubre con un **test unitario directo
> al servicio**, no con un test E2E (ver plan TDD, tarea 9).

## Decisiones tomadas (para que la implementación no dude)

1. **Trash + campos adicionales en la misma llamada → rechazo total.**
   `PATCH {"status":"draft","title":"x"}` sobre un post en trash devuelve
   `422 TRASH_POST_LOCKED` sin aplicar nada. Restaurar y editar son 2 llamadas.
2. **PUT preserva `status` y `author_id` si se omiten del body.** Un PUT que no
   incluye `status` no lo resetea a `draft`; un PUT sin `author_id` no lo pone en
   `null`. Sí se resetean `excerpt` y `slug` a su default (`null` / regenerado)
   si se omiten, porque esos campos no tienen efectos colaterales de negocio.
   `title` y `content` siempre son obligatorios en PUT.
   La autogeneración de `slug` por omisión aplica **solo a PUT**: en PATCH,
   omitir `slug` simplemente lo preserva (semántica normal de update parcial),
   no lo regenera.
3. **Slug duplicado en Update → 400, no autosufijo.** A diferencia de Store
   (que autogenera y sufija en creación), si el cliente pasa explícitamente un
   `slug` que ya usa otro post, se rechaza con `VALIDATION_ERROR` — no se
   inventa un slug distinto al que pidió.
4. **`updated_at` se actualiza en toda request aceptada (200)**, incluidos los
   no-ops de estado (ej. `PATCH {"status":"publish"}` sobre un post que ya
   estaba publicado). Simplifica el contrato: si la respuesta es 200, `updated_at`
   cambió.
5. **Post en trash, PATCH `{"status":"trash"}` (no-op)** → se permite, 200, sin
   tocar `deleted_at` (no se reinicia el reloj de borrado), pero sí bumpea
   `updated_at` (ver decisión 4).
6. **Las transiciones de `status` sí se validan en esta spec.** Esto responde
   afirmativamente al punto abierto "validar si el equipo lo considera
   necesario": el motor completo de `PostStateService` se implementa en Spec 4,
   no se deja pendiente ni se simplifica a un simple `UPDATE` de columna.

## Criterios de aceptación

**PATCH — parcial**
- Un PATCH con `{"title": "nuevo"}` sobre un post en `draft` devuelve `200`, cambia solo `title` y `updated_at`, y preserva el resto de los campos.
- Un PATCH sobre un `id` inexistente devuelve `404 POST_NOT_FOUND`, sin importar el body.
- Un PATCH con body vacío (`{}`) devuelve `400 VALIDATION_ERROR`.
- Un PATCH con `{"title": ""}` devuelve `400 VALIDATION_ERROR` sobre el campo `title`.
- Un PATCH con `{"author_id": 9999}` (usuario inexistente) devuelve `400 VALIDATION_ERROR` sobre el campo `author_id`.
- Un PATCH sobre el post A con un `slug` ya usado por el post B devuelve `400 VALIDATION_ERROR` sobre el campo `slug`.

**PUT — total**
- Un PUT con `title` y `content` completos devuelve `200` y reemplaza todos los campos de contenido.
- Un PUT sin `title` devuelve `400 VALIDATION_ERROR`.
- Un PUT sin `status` en el body no resetea el post a `draft`; conserva el `status` que tenía (por ejemplo, `publish`).
- Un PUT sin `author_id` en el body conserva el `author_id` que tenía.

**Transición a `publish`**
- Un PATCH `{"status": "publish"}` sobre un post `draft` con `title`/`content` no vacíos devuelve `200`, cambia `status` a `publish` y setea `published_at` a la hora actual.
- Volver a publicar un post ya publicado (no-op, o un PATCH que lo mantiene en `publish`) no cambia `published_at` (conserva su valor original), pero sí actualiza `updated_at`.

**Transición a `trash` / restauración**
- Un PATCH `{"status": "trash"}` sobre un post en cualquier estado no-trash devuelve `200` y setea `deleted_at` a la hora actual.
- Un PATCH `{"title": "x"}` (sin `status`) sobre un post en `trash` devuelve `422 TRASH_POST_LOCKED`.
- Un PATCH `{"status": "draft", "title": "x"}` sobre un post en `trash` también devuelve `422 TRASH_POST_LOCKED` (rechazo total, ver Decisión #1).
- Un PATCH `{"status": "draft"}` (solo `status`) sobre un post en `trash` devuelve `200`, limpia `deleted_at` y cambia `status` a `draft`.
- Un PATCH `{"status": "trash"}` sobre un post que ya está en `trash` (no-op) devuelve `200` sin modificar `deleted_at`.

**Contratos generales**
- Toda respuesta exitosa de update serializa exactamente los 11 campos de `PostRead` definidos en Spec 0.
- El cliente no puede modificar `id` ni `created_at` aunque los envíe en el body; el valor persistido nunca cambia.

## Fuera de alcance

- ❌ Historial de revisiones / versionado de contenido
- ❌ Endpoint dedicado de restauración (`POST /posts/{id}/restore`) — se restaura vía `PATCH status`
- ❌ Autosufijo de slug en Update (sí existe en Store/Spec 3)
- ❌ Notificaciones o webhooks al cambiar de estado

## Salidas de Spec 4 (Definition of Done)

- [ ] `PostStateService` implementado completo (reemplaza el stub de Spec 0) → `app/services/post_state.py`
- [ ] Interfaz **sin cambios de firma** respecto a lo publicado en Spec 0 (P6 no debe tocar su código)
- [ ] Schemas `PostUpdate`, `PostReplace` → `app/schemas/post.py`
- [ ] Handlers `PATCH /posts/{id}` y `PUT /posts/{id}` → `app/routers/posts.py`
- [ ] Excepciones `InvalidStatusTransition`, `TrashPostLocked` conectadas al handler global de Spec 0
- [ ] Tests unitarios de `PostStateService` (incluye el caso defensivo de publish vacío)
- [ ] Tests de integración (TestClient) de `PATCH`/`PUT` cubriendo todos los criterios de aceptación
- [ ] Suite E2E (`tests/e2e/test_update_e2e.py`) en verde
- [ ] Colección Postman con todos los escenarios, corriendo en verde (Newman o Postman Runner)
- [ ] `doc/ai/plans/04-update.md` (este documento) enlazado desde el README
- [ ] PR a `main`, tests de las demás specs siguen en verde

> El mapa de archivos y el detalle técnico de cómo se implementa todo esto
> (arquitectura, tareas TDD paso a paso, código) viven en el Implementation
> Plan enlazado al principio de este documento — no en la spec.