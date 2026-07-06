from app.models.post import Post
from app.models.user import User
from app.services.post_query import list_posts


def _post(db, slug, **kw):
    defaults = {"title": "t", "content": "c", "status": "draft"}
    defaults.update(kw)
    post = Post(slug=slug, **defaults)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def test_pagination_counts(db_session):
    for i in range(15):
        _post(db_session, slug=f"s{i}")
    items, total = list_posts(db_session, page=1, per_page=10)
    assert total == 15
    assert len(items) == 10


def test_second_page_returns_remainder(db_session):
    for i in range(15):
        _post(db_session, slug=f"s{i}")
    items, total = list_posts(db_session, page=2, per_page=10)
    assert len(items) == 5


def test_trash_hidden_by_default(db_session):
    _post(db_session, slug="a", status="draft")
    _post(db_session, slug="b", status="trash")
    items, total = list_posts(db_session)
    assert total == 1
    assert all(p.status != "trash" for p in items)


def test_status_trash_returns_only_trash(db_session):
    _post(db_session, slug="a", status="draft")
    _post(db_session, slug="b", status="trash")
    items, total = list_posts(db_session, status="trash")
    assert total == 1
    assert items[0].status == "trash"


def test_search_matches_title_and_content(db_session):
    _post(db_session, slug="a", title="Hola Mundo", content="x")
    _post(db_session, slug="b", title="Otro", content="aqui dice HOLA")
    _post(db_session, slug="c", title="Nada", content="nope")
    items, total = list_posts(db_session, search="hola")
    assert total == 2


def test_filter_by_author(db_session):
    u1 = User(name="Ana", email="a@e.com")
    u2 = User(name="Luis", email="l@e.com")
    db_session.add_all([u1, u2])
    db_session.commit()
    _post(db_session, slug="a", author_id=u1.id)
    _post(db_session, slug="b", author_id=u2.id)
    items, total = list_posts(db_session, author=u1.id)
    assert total == 1
    assert items[0].author_id == u1.id


def test_orderby_title_asc(db_session):
    _post(db_session, slug="a", title="Banana")
    _post(db_session, slug="b", title="Apple")
    items, _ = list_posts(db_session, orderby="title", order="asc")
    assert [p.title for p in items] == ["Apple", "Banana"]


def test_empty_db(db_session):
    items, total = list_posts(db_session)
    assert items == []
    assert total == 0
