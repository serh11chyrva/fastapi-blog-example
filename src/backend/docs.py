"""Serve the current API contract without starting application infrastructure."""

from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from backend.core.api_docs import add_api_reference
from backend.main import app as api_app


def create_app() -> FastAPI:
    """Expose only documentation routes; API operations remain schema entries."""
    app = FastAPI(
        title=api_app.title,
        version=api_app.version,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    def preview_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = deepcopy(api_app.openapi())
            schema["info"]["description"] = (
                "**Documentation preview.** This server only serves the API reference and "
                "OpenAPI schema. API requests and file uploads are unavailable. "
                "Examples describe the full application and are not live data.\n\n"
                + schema["info"].get("description", "")
            )
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = preview_openapi
    add_api_reference(app, documentation_only=True)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/api/docs")

    return app


app = create_app()
