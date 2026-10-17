import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app


@pytest.mark.asyncio
async def test_mutating_api_rejects_foreign_origin_before_dispatch() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8080"
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            headers={"Origin": "https://attacker.example"},
            json={
                "email": "user@example.com",
                "username": "writer",
                "display_name": "Writer",
                "password": "long-enough-password",
            },
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_openapi_exposes_the_versioned_auth_and_publication_routes() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8080"
    ) as client:
        response = await client.get("/api/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/sessions/logout-others" in paths
    assert "/api/v1/feeds/public" in paths
    assert "/api/v1/articles/{article_id}/publish" in paths
