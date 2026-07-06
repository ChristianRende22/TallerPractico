from app.schemas.post import Pagination, PostList


def test_postlist_has_data_and_pagination():
    assert set(PostList.model_fields) == {"data", "pagination"}


def test_postlist_constructs_empty():
    obj = PostList(
        data=[],
        pagination=Pagination(total=0, page=1, per_page=10, total_pages=0),
    )
    assert obj.data == []
    assert obj.pagination.total == 0
