"""Typed access to application-owned infrastructure clients."""

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request
from geoip2.database import Reader
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from backend.storage.s3 import S3Client


@dataclass(frozen=True, slots=True)
class AppResources:
    """Typed container for application-owned infrastructure clients."""

    mongo: AsyncMongoClient
    redis: Redis
    s3: S3Client
    s3_public: S3Client
    geoip: Reader | None = None


def get_resources(request: Request) -> AppResources:
    """Read the typed infrastructure clients from application state.

    :param request: Incoming HTTP request and its application state.
    :return: The application resource container.
    """
    return cast(AppResources, request.app.state.resources)


Resources = Annotated[AppResources, Depends(get_resources)]
