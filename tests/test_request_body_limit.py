
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.body_limit import RequestBodyLimitMiddleware


def create_test_app():
    test_app = FastAPI()

    test_app.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_size=100,
    )

    @test_app.post("/upload")
    async def upload():
        return {"status": "accepted"}

    return test_app


def test_accepts_request_within_limit():
    client = TestClient(create_test_app())

    response = client.post("/upload", content=b"x" * 100)

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_rejects_request_larger_than_limit():
    client = TestClient(create_test_app())

    response = client.post("/upload", content=b"x" * 101)

    assert response.status_code == 413
