from datetime import datetime, timezone

from app.errors.exceptions import InvalidStatusTransition


class PostStateService:
    """Motor de transiciones de estado de Post. Implementado en Spec 4 (P5)."""

    def can_transition(self, post, new_status: str) -> bool:
        if new_status == "publish":
            return bool(post.title) and bool(post.content)
        return True

    def transition(self, post, new_status: str):
        if new_status == post.status:
            return post

        if new_status == "publish":
            if not self.can_transition(post, new_status):
                raise InvalidStatusTransition(
                    "Cannot publish a post with empty title or content"
                )
            if post.published_at is None:
                post.published_at = datetime.now(timezone.utc)

        if new_status == "trash":
            post.deleted_at = datetime.now(timezone.utc)
        elif post.status == "trash":
            post.deleted_at = None

        post.status = new_status
        return post
