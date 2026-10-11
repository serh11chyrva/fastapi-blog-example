from contextlib import asynccontextmanager
from os import environ
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = AsyncIOMotorClient(environ.get("MONGODB_URL", "mongodb://localhost:27017"))
    await client.admin.command("ping")
    app.state.mongo_client = client
    app.state.database = client[environ.get("MONGODB_DATABASE", "blog")]
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="FastAPI Blog Example", lifespan=lifespan)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"message": "FastAPI Blog Example"}


@app.get("/health", tags=["health"])
async def health(request: Request) -> dict[str, str]:
    try:
        await request.app.state.mongo_client.admin.command("ping")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from exc
    return {"status": "ok", "database": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("fastapi_blog_example.main:app", host="0.0.0.0", port=8000)
