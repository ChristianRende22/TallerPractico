def test_full_post_lifecycle(client, db_session):
    from tests.integration.test_update import _seed_post

    post = _seed_post(db_session)

    r1 = client.patch(f"/posts/{post.id}", json={"title": "Editado"})
    assert r1.status_code == 200

    r2 = client.put(f"/posts/{post.id}", json={"title": "Reemplazado", "content": "Nuevo"})
    assert r2.status_code == 200

    r3 = client.patch(f"/posts/{post.id}", json={"status": "publish"})
    assert r3.status_code == 200
    assert r3.json()["published_at"] is not None

    r4 = client.patch(f"/posts/{post.id}", json={"status": "trash"})
    assert r4.status_code == 200
    assert r4.json()["deleted_at"] is not None

    r5 = client.patch(f"/posts/{post.id}", json={"title": "no permitido"})
    assert r5.status_code == 422

    r6 = client.patch(f"/posts/{post.id}", json={"status": "draft"})
    assert r6.status_code == 200
    assert r6.json()["deleted_at"] is None
