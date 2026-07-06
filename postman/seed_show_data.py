"""Seed de datos de demo para la coleccion Postman de Spec 2 (Show).

Inserta dos posts dedicados para probar:
- caso feliz: post existente en draft
- caso trash: post existente en trash

Requiere que la migracion ya haya corrido:
    python -m alembic upgrade head

Uso:
    python postman/seed_show_data.py

El script limpia la tabla posts y vuelve a sembrar los registros en un orden
deterministico para que los ids queden estables entre ejecuciones.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.post import Post


SCENARIOS = [
    (
        "show_happy",
        dict(
            title="Show Happy",
            content="Contenido del post happy",
            slug="show-happy",
            status="draft",
            author_id=1,
        ),
    ),
    (
        "show_trash",
        dict(
            title="Show Trash",
            content="Contenido del post trash",
            slug="show-trash",
            status="trash",
            author_id=2,
            deleted_at=datetime.now(timezone.utc),
        ),
    ),
]


def main():
    db = SessionLocal()
    try:
        db.query(Post).delete()
        db.commit()

        ids = {}
        for name, fields in SCENARIOS:
            post = Post(**fields)
            db.add(post)
            db.commit()
            db.refresh(post)
            ids[name] = post.id

        print(f"{'escenario':<20} id")
        print("-" * 25)
        for name, post_id in ids.items():
            print(f"{name:<20} {post_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()