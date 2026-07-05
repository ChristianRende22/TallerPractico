from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.errors.exceptions import InvalidStatusTransition
from app.services.post_state import PostStateService


def _post(**overrides):
    base = dict(
        status="draft", title="T", content="C", published_at=None, deleted_at=None
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.parametrize(
    "current,new",
    [
        ("draft", "publish"),
        ("pending", "trash"),
        ("trash", "draft"),
        ("publish", "publish"),
        ("trash", "trash"),
    ],
)
def test_can_transition_true_for_any_pair(current, new):
    assert PostStateService().can_transition(_post(status=current), new) is True


def test_can_transition_false_only_for_publish_with_empty_fields():
    assert PostStateService().can_transition(_post(content=""), "publish") is False
    assert PostStateService().can_transition(_post(title=""), "publish") is False


def test_transition_to_publish_sets_published_at_first_time():
    post = _post(status="draft")
    PostStateService().transition(post, "publish")
    assert post.status == "publish"
    assert post.published_at is not None


def test_transition_to_publish_again_keeps_original_published_at():
    original = datetime(2026, 1, 1, tzinfo=timezone.utc)
    post = _post(status="publish", published_at=original)
    PostStateService().transition(post, "publish")
    assert post.published_at == original


def test_transition_to_publish_raises_when_content_empty():
    post = _post(status="draft", content="")
    with pytest.raises(InvalidStatusTransition):
        PostStateService().transition(post, "publish")


def test_transition_to_trash_sets_deleted_at():
    post = _post(status="draft")
    PostStateService().transition(post, "trash")
    assert post.status == "trash"
    assert post.deleted_at is not None


def test_transition_out_of_trash_clears_deleted_at():
    post = _post(status="trash", deleted_at=datetime.now(timezone.utc))
    PostStateService().transition(post, "draft")
    assert post.status == "draft"
    assert post.deleted_at is None


def test_same_status_noop_does_not_touch_dates():
    post = _post(status="trash", deleted_at=None)
    PostStateService().transition(post, "trash")
    assert post.deleted_at is None
