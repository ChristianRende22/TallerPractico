# Spec 5 — Delete Post

**Persona:** P6 · **Endpoint:** `DELETE /posts/{id}`  
**Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Pytest  
**Base:** Spec 0 — Foundation  
**Estado:** Pendiente

---

## Objetivo

Implementar la eliminación de posts respetando el contrato fundacional:

- Por defecto, `DELETE /posts/{id}` hace **soft delete**.
- Con `?force=true`, `DELETE /posts/{id}?force=true` hace **eliminación permanente**.
- Ambos comportamientos deben estar cubiertos con tests.

La eliminación lógica usa el estado canónico `trash`, ya definido en `POST_STATUSES`.
La eliminación permanente borra el registro de la tabla `posts`.

---

## Alcance

### 1. Soft delete por defecto

**Endpoint**

```http
DELETE /posts/{id}
```

**Comportamiento**

Cuando el post existe:

- No se elimina el registro de la base de datos.
- El post pasa a `status = "trash"`.
- Se setea `deleted_at` con la fecha/hora actual.
- Se conserva el resto de la información del post.
- La respuesta devuelve el contrato canónico `PostRead`.

**Respuesta esperada**

```http
200 OK
```

```json
{
  "id": 1,
  "title": "Mi post",
  "content": "Contenido...",
  "excerpt": null,
  "slug": "mi-post",
  "status": "trash",
  "author_id": 1,
  "created_at": "2026-07-03T10:30:00Z",
  "updated_at": "2026-07-06T12:00:00Z",
  "published_at": null,
  "deleted_at": "2026-07-06T12:00:00Z"
}
```

**Regla de idempotencia**

Si el post ya está en `trash` y se llama nuevamente sin `force=true`:

- Responde `200 OK`.
- Mantiene `status = "trash"`.
- No elimina el registro.
- No debe fallar con `TRASH_POST_LOCKED`, porque delete no es update de campos de contenido.

---

### 2. Eliminación permanente

**Endpoint**

```http
DELETE /posts/{id}?force=true
```

**Comportamiento**

Cuando el post existe:

- Se elimina físicamente el registro de la tabla `posts`.
- La operación es irreversible.
- No se devuelve cuerpo de respuesta.

**Respuesta esperada**

```http
204 No Content
```

Después de la eliminación permanente, una consulta posterior al mismo `id` debe comportarse como post inexistente.

---

### 3. Post inexistente

Aplica para ambos modos:

```http
DELETE /posts/{id}
DELETE /posts/{id}?force=true
```

Si el post no existe:

```http
404 Not Found
```

Con el formato estándar de errores de Spec 0:

```json
{
  "error": "Post not found",
  "code": "POST_NOT_FOUND",
  "status": 404,
  "details": []
}
```

La implementación debe lanzar `PostNotFound`; no debe construir JSON de error manualmente.

---

## Contrato de implementación

### Archivos permitidos

Según Spec 0, P2–P6 trabajan únicamente en:

```txt
app/routers/posts.py
app/schemas/
tests/
```

No se deben modificar archivos congelados de Spec 0.

### Reglas técnicas

- Usar `get_db()` para la sesión.
- Buscar el post por `id`.
- Si no existe, lanzar `PostNotFound`.
- Para soft delete, usar `PostStateService.transition(post, "trash")`.
- Spec 5 depende de Spec 4: `PostStateService` debe estar implementado antes de integrar Delete.
- La operación soft delete debe actualizar `updated_at` en toda respuesta `200`, incluso cuando el post ya estaba en `trash`.
- Si el post ya estaba en `trash`, `PostStateService.transition(post, "trash")` debe tratarlo como no-op de estado: no debe reasignar `deleted_at`.
- La regla `TRASH_POST_LOCKED` no aplica a `DELETE`, porque este endpoint no modifica campos editables del post.
- Para `force=true`, no usar `PostStateService`; eliminar el registro directamente con `db.delete(post)` y `db.commit()`.
- La respuesta soft delete debe usar `PostRead`.
- La respuesta force delete debe ser `204 No Content`.

---

## Criterios de aceptación Given/When/Then

### Soft delete

- **Given** existe un post con `status != "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** responde `200 OK`.

- **Given** existe un post con `status != "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** la respuesta cumple exactamente el contrato `PostRead` de 11 campos.

- **Given** existe un post con `status != "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** el post queda en base de datos con `status = "trash"`.

- **Given** existe un post con `status != "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** `deleted_at` queda informado.

- **Given** existe un post con `status != "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** `updated_at` se actualiza con la fecha/hora actual.

### Soft delete idempotente

- **Given** existe un post con `status = "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** responde `200 OK`.

- **Given** existe un post con `status = "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** el registro sigue existiendo en base de datos.

- **Given** existe un post con `status = "trash"` y `deleted_at` informado,
  **When** se hace `DELETE /posts/{id}`,
  **Then** conserva el valor original de `deleted_at`.

- **Given** existe un post con `status = "trash"`,
  **When** se hace `DELETE /posts/{id}`,
  **Then** `updated_at` se actualiza con la fecha/hora actual.

### Eliminación permanente

- **Given** existe un post,
  **When** se hace `DELETE /posts/{id}?force=true`,
  **Then** responde `204 No Content`.

- **Given** existe un post,
  **When** se hace `DELETE /posts/{id}?force=true`,
  **Then** el registro ya no existe en la base de datos.

- **Given** un post fue eliminado permanentemente,
  **When** se intenta eliminar otra vez con cualquier modo,
  **Then** responde `404 POST_NOT_FOUND`.

### Post inexistente

- **Given** no existe un post con id `999`,
  **When** se hace `DELETE /posts/999`,
  **Then** responde `404 POST_NOT_FOUND`.

- **Given** no existe un post con id `999`,
  **When** se hace `DELETE /posts/999?force=true`,
  **Then** responde `404 POST_NOT_FOUND`.

---

## Tests mínimos requeridos

Crear tests en `tests/`, por ejemplo:

```txt
tests/test_posts_delete.py
```

Casos mínimos:

1. `test_delete_post_soft_deletes_by_default`
2. `test_delete_post_soft_delete_returns_post_contract`
3. `test_delete_post_soft_delete_keeps_record_in_database`
4. `test_delete_post_force_true_permanently_deletes_record`
5. `test_delete_post_force_true_returns_204_no_content`
6. `test_delete_missing_post_returns_404`
7. `test_force_delete_missing_post_returns_404`
8. `test_soft_delete_already_trashed_post_is_idempotent`
9. `test_delete_post_soft_delete_updates_updated_at`
10. `test_soft_delete_already_trashed_post_preserves_deleted_at`
11. `test_soft_delete_already_trashed_post_updates_updated_at`

---

## Fuera de alcance

- Restaurar posts desde `trash`.
- Autorización o permisos para borrar.
- Auditoría de quién eliminó el post.
- Eliminación en cascada de entidades relacionadas.
- Cambiar el contrato `PostRead`.
- Cambiar el formato estándar de errores.
- Cambiar `POST_STATUSES`.

---

## Definition of Done

- [ ] `DELETE /posts/{id}` implementado como soft delete.
- [ ] `DELETE /posts/{id}?force=true` implementado como eliminación permanente.
- [ ] Soft delete conserva el registro en base de datos.
- [ ] Force delete elimina el registro de base de datos.
- [ ] Post inexistente responde `404 POST_NOT_FOUND`.
- [ ] Soft delete devuelve `PostRead`.
- [ ] Force delete devuelve `204 No Content` sin body.
- [ ] Tests cubren ambos modos.
- [ ] Toda la suite de tests pasa.
- [ ] Soft delete cambia `status` a `trash`.
- [ ] Soft delete setea `deleted_at` cuando el post no estaba en `trash`.
- [ ] Soft delete actualiza `updated_at` en toda respuesta `200`.
- [ ] Soft delete idempotente conserva `deleted_at`.