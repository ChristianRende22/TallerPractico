from fastapi import FastAPI

from app.routers import health, posts


def create_app() -> FastAPI:
    app = FastAPI(title="CMS Posts API")
    app.include_router(health.router)
    app.include_router(posts.router)
    return app


app = create_app()
