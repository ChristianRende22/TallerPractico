import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors.exceptions import PostNotFound
from app.errors.handlers import register_error_handlers


class _Item(BaseModel):
    title: str


@pytest.fixture
def error_client():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom-notfound")
    def boom_notfound():
        raise PostNotFound()

    @app.get("/boom-500")
    def boom_500():
        raise RuntimeError("kaboom")

    @app.post("/need-title")
    def need_title(item: _Item):
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


def test_app_error_shape(error_client):
    response = error_client.get("/boom-notfound")
    assert response.status_code == 404
    assert response.json() == {
        "error": "Post not found",
        "code": "POST_NOT_FOUND",
        "status": 404,
    }


def test_internal_error_shape(error_client):
    response = error_client.get("/boom-500")
    assert response.status_code == 500
    assert response.json() == {
        "error": "Internal server error",
        "code": "INTERNAL_ERROR",
        "status": 500,
    }


def test_pydantic_validation_translated_to_400(error_client):
    response = error_client.post("/need-title", json={})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["status"] == 400
    assert any(detail["field"] == "title" for detail in body["details"])
