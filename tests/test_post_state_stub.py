import pytest

from app.services.post_state import PostStateService


def test_can_transition_not_implemented():
    with pytest.raises(NotImplementedError):
        PostStateService().can_transition(object(), "publish")


def test_transition_not_implemented():
    with pytest.raises(NotImplementedError):
        PostStateService().transition(object(), "trash")
