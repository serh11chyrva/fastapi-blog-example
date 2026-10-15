"""Shared conflict policy for audited MongoDB operations."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import OperationFailure

from backend.core.errors import Conflict


@asynccontextmanager
async def transaction(client: AsyncMongoClient) -> AsyncIterator[AsyncClientSession]:
    """Commit once or report a conflict; callers explicitly reconcile before retrying.

    The body may allocate IDs or perform other non-repeatable work. It is never
    replayed automatically. An unknown commit outcome propagates as a database
    failure so clients can reload instead of assuming that the write was undone.
    """
    try:
        async with client.start_session() as session:
            async with await session.start_transaction():
                yield session
    except OperationFailure as exc:
        if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
            raise Conflict("The resource changed; reload before retrying") from exc
        raise
