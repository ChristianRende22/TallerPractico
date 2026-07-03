# Colección Postman — CMS Posts API

`CMS-Posts-API.postman_collection.json` cubre:

- **Health** — `GET /health`
- **Posts - Index (Spec 1)** — `GET /posts` con paginación, búsqueda, filtros
  (status/author), ordenamiento y casos de error 400.

Cada request trae scripts de test (pestaña *Tests*) que validan status code y forma
de la respuesta.

## Cómo usarla

1. **Levantar la API** (desde la raíz del repo):
   ```bash
   python -m pip install -r requirements.txt
   python -m alembic upgrade head            # crea posts.db con schema + seed de users
   python -m uvicorn app.main:app --reload   # http://127.0.0.1:8000
   ```

2. **Importar en Postman:** File → Import → seleccionar
   `postman/CMS-Posts-API.postman_collection.json`.

3. La variable de colección `baseUrl` ya apunta a `http://127.0.0.1:8000`.
   Cambiala si corrés en otro host/puerto.

4. Correr requests individuales o toda la colección con el **Collection Runner**.

## Nota sobre datos

La migración siembra 2 **usuarios** (Ana, Luis) pero **no posts**. Con la BD recién
migrada, `GET /posts` responde `200` con `data: []` — el endpoint funciona, solo que
no hay contenido todavía.

Para ver posts reales necesitás `POST /posts` (Spec 3, aún pendiente) o insertar filas
a mano, por ejemplo:

```bash
python - <<'PY'
from app.database import SessionLocal
from app.models.post import Post
db = SessionLocal()
db.add_all([
    Post(title="Hola Mundo", content="primer post", slug="hola-mundo", status="publish", author_id=1),
    Post(title="Borrador", content="wip", slug="borrador", status="draft", author_id=1),
    Post(title="En papelera", content="x", slug="papelera", status="trash", author_id=2),
])
db.commit()
print("posts insertados")
PY
```

## Correr la colección por CLI (opcional)

Con [newman](https://github.com/postmanlabs/newman):

```bash
npm install -g newman
newman run postman/CMS-Posts-API.postman_collection.json
```
