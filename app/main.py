from fastapi import FastAPI

from app.errors.handlers import register_error_handlers
from app.routers import health, posts


def create_app() -> FastAPI:
    app = FastAPI(title="CMS Posts API")
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(posts.router)
    return app


app = create_app()
