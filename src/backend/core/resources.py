"""Typed access to application-owned infrastructure clients."""

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from backend.storage.s3 import S3Client


@dataclass(frozen=True, slots=True)
class AppResources:
    mongo: AsyncMongoClient
    redis: Redis
    s3: S3Client
    s3_public: S3Client


def get_resources(request: Request) -> AppResources:
    return cast(AppResources, request.app.state.resources)


Resources = Annotated[AppResources, Depends(get_resources)]
