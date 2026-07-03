from fastapi import APIRouter

# Router base de /posts. Vacío en Spec 0.
# P2–P6 agregan aquí sus endpoints; no se toca la fundación.
router = APIRouter(prefix="/posts", tags=["posts"])
