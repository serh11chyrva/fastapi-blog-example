"""Explicitly prepare Atlas Search indexes or inspect their readiness."""

import argparse
import asyncio
import json
import time
from typing import Any

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.operations import SearchIndexModel

from backend.core.config import get_settings
from backend.core.database import DOCUMENT_MODELS
from backend.search.indexes import INDEX_DEFINITIONS


def definition_matches(actual: Any, expected: Any) -> bool:
    """Compare declared index settings while allowing server-supplied defaults.

    :param actual: Atlas's current index definition or a nested value.
    :param expected: Versioned settings declared by this application.
    :return: Whether all declared settings are present with the intended values.
    """
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and definition_matches(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            definition_matches(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


async def manage(operation: str, timeout: int) -> None:
    """Provision versioned indexes and await readiness, or print current index status.

    Search index management is an explicit PyMongo integration; ordinary content
    reads and writes use Beanie. API startup never performs this potentially long task.

    :param operation: setup creates missing indexes; status performs read-only inspection.
    :param timeout: Maximum seconds to await queryable indexes after setup.
    :return: None; failures and readiness timeouts exit unsuccessfully.
    """
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb_url, serverSelectionTimeoutMS=8_000)
    try:
        database = client[settings.mongodb_database]
        if operation == "setup":
            await init_beanie(database=database, document_models=DOCUMENT_MODELS)
        for name, (collection_name, definition) in INDEX_DEFINITIONS.items():
            collection = database[collection_name]
            existing = await (await collection.list_search_indexes(name=name)).to_list()
            if operation == "status":
                print(json.dumps({"collection": collection_name, "index": name, "status": existing}, default=str))
                continue
            if not existing:
                await collection.create_search_index(SearchIndexModel(name=name, definition=definition))
            elif not definition_matches(existing[0].get("latestDefinition"), definition):
                await collection.update_search_index(name, definition)
            deadline = time.monotonic() + timeout
            while True:
                current = await (await collection.list_search_indexes(name=name)).to_list()
                if current and current[0].get("status") == "FAILED":
                    raise RuntimeError(f"Atlas index {name} failed: {current[0].get('statusDetail')}")
                if (current and current[0].get("queryable") and current[0].get("status") == "READY"
                        and definition_matches(current[0].get("latestDefinition"), definition)):
                    print(f"{collection_name}/{name} is ready.", flush=True)
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Atlas index {name} was not ready within {timeout} seconds")
                await asyncio.sleep(2)
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["setup", "status"])
    parser.add_argument("--timeout", type=int, default=600)
    arguments = parser.parse_args()
    asyncio.run(manage(arguments.operation, arguments.timeout))
