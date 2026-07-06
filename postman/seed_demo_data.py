"""Seed de datos de demo para la coleccion Postman de Spec 4 (Update).

Store (Spec 3) todavia no expone POST /posts en esta rama, asi que no hay
forma de crear posts via HTTP. Este script inserta un post dedicado por cada
escenario de la coleccion directo en la BD, reutilizando los mismos modelos
que usa la app (app.database, app.models). Requiere que la migracion ya haya
corrido (python -m alembic upgrade head) para que existan los usuarios
sembrados Ana (id=1) y Luis (id=2).

Uso:
    python postman/seed_demo_data.py

Vacia la tabla posts y vuelve a sembrarla, asi los ids quedan deterministicos
(1, 2, 3, ... en el mismo orden en que se listan aqui). Se imprime la tabla
escenario -> id al final.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.post import Post

PAST_PUBLISHED_AT = datetime(2020, 1, 1, tzinfo=timezone.utc)

# (nombre del escenario, kwargs para construir el Post)
SCENARIOS = [
    ("patch_happy", dict(title="Patch Happy", content="Contenido original", slug="patch-happy", author_id=1)),
    ("put_happy", dict(title="Put Happy", content="Contenido original", slug="put-happy", author_id=1)),
    ("patch_empty_body", dict(title="Patch Empty Body", content="C", slug="patch-empty-body", author_id=1)),
    ("patch_empty_title", dict(title="Patch Empty Title", content="C", slug="patch-empty-title", author_id=1)),
    ("put_missing_title", dict(title="Put Missing Title", content="C", slug="put-missing-title", author_id=1)),
    ("patch_invalid_author", dict(title="Patch Invalid Author", content="C", slug="patch-invalid-author", author_id=1)),
    ("slug_a", dict(title="Slug A", content="C", slug="slug-a", author_id=1)),
    ("slug_b", dict(title="Slug B", content="C", slug="slug-b", author_id=1)),
    ("trash_field_locked", dict(title="Trash Field Locked", content="C", slug="trash-field-locked", author_id=2, status="trash", deleted_at=datetime.now(timezone.utc))),
    ("trash_restore_and_edit", dict(title="Trash Restore And Edit", content="C", slug="trash-restore-and-edit", author_id=2, status="trash", deleted_at=datetime.now(timezone.utc))),
    ("trash_restore_only", dict(title="Trash Restore Only", content="C", slug="trash-restore-only", author_id=2, status="trash", deleted_at=datetime.now(timezone.utc))),
    ("trash_noop", dict(title="Trash Noop", content="C", slug="trash-noop", author_id=2, status="trash", deleted_at=datetime.now(timezone.utc))),
    ("publish_first_time", dict(title="Publish First Time", content="C", slug="publish-first-time", author_id=1)),
    ("publish_again", dict(title="Publish Again", content="C", slug="publish-again", author_id=1, status="publish", published_at=PAST_PUBLISHED_AT)),
    ("put_preserve_status", dict(title="Put Preserve Status", content="C", slug="put-preserve-status", author_id=1, status="publish", published_at=PAST_PUBLISHED_AT)),
    ("put_preserve_author", dict(title="Put Preserve Author", content="C", slug="put-preserve-author", author_id=2)),
    ("put_regen_slug", dict(title="Put Regen Slug Original", content="C", slug="original-slug", author_id=1)),
    ("contract_fields", dict(title="Contract Fields", content="C", slug="contract-fields", author_id=1)),
    ("immutable_fields", dict(title="Immutable Fields", content="C", slug="immutable-fields", author_id=1)),
    ("e2e_lifecycle", dict(title="E2E Lifecycle", content="C", slug="e2e-lifecycle", author_id=1)),
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

        print(f"{'escenario':<28} id")
        print("-" * 34)
        for name, post_id in ids.items():
            print(f"{name:<28} {post_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
