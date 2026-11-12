"""Build bounded Atlas queries and query-bound opaque continuation cursors."""

import base64
import hashlib
import json
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal

from backend.core.errors import InvalidOperation
from backend.publications.hashtags import hashtag_character, hashtag_spans, normalize_tag, validate_tag

type SearchSort = Literal["relevance", "latest"]
INDEX_VERSION = 1
PUBLICATIONS_INDEX = "search_publications_v1"
USERS_INDEX = "search_users_v1"


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Normalized text terms and mandatory exact hashtag filters."""

    terms: tuple[str, ...]
    hashtags: tuple[str, ...]


def parse_query(value: str) -> SearchQuery:
    """Parse literal query text without exposing Atlas query-language syntax.

    :param value: User query containing up to 200 characters and optional hashtags.
    :return: Normalized words and deduplicated mandatory hashtags.
    """
    if len(value) > 200:
        raise InvalidOperation("Search queries must contain at most 200 characters")
    spans = hashtag_spans(value, max_length=None)
    try:
        for _, _, tag in spans:
            validate_tag(tag)
    except ValueError as exc:
        raise InvalidOperation(str(exc)) from exc
    remaining = list(value)
    for start, end, _ in spans:
        remaining[start:end] = " " * (end - start)
    words = "".join(character if hashtag_character(character) else " " for character in remaining)
    terms = tuple(unicodedata.normalize("NFC", word).lower() for word in words.split())
    tags = tuple(sorted({normalize_tag(tag) for _, _, tag in spans}))
    if (not terms and not tags) or (terms and sum(map(len, terms)) < 2):
        raise InvalidOperation("Enter at least two text characters or a valid hashtag")
    return SearchQuery(terms, tags)


def atlas_query(query: SearchQuery, *, users: bool, sort: SearchSort, after: str | None) -> dict[str, Any]:
    """Build one conjunctive query with exact terms, last-word prefixes, and bounded fuzzy alternatives.

    :param query: Parsed literal terms and exact hashtag filters.
    :param users: Whether to search public user fields instead of publication text.
    :param sort: Requested publication ordering; users always use relevance.
    :param after: Atlas searchSequenceToken from the same query, or None.
    :return: The complete first-stage Atlas search specification.
    """
    fields = {"username": 32, "display_name": 4, "bio": 1} if users else {"title": 3, "text": 1}
    must = []
    for index, term in enumerate(query.terms):
        alternatives = []
        for field, weight in fields.items():
            alternatives.append({"text": {
                "path": field, "query": term, "matchCriteria": "all",
                "score": {"constant": {"value": weight * 8}},
            }})
            if len(term) >= 4:
                alternatives.append({"text": {
                    "path": field, "query": term,
                    "matchCriteria": "all",
                    "fuzzy": {"maxEdits": 1, "prefixLength": 0, "maxExpansions": 20},
                    "score": {"constant": {"value": weight}},
                }})
            if index == len(query.terms) - 1 and len(term) >= 2:
                alternatives.append({"autocomplete": {
                    "path": field, "query": term, "tokenOrder": "sequential",
                    "score": {"constant": {"value": weight * 2}},
                }})
        must.append({"compound": {"should": alternatives, "minimumShouldMatch": 1}})
    compound: dict[str, Any] = {}
    if must:
        compound["must"] = must
    if query.hashtags:
        path = "search_hashtags" if users else "hashtags"
        compound["filter"] = [{"equals": {"path": path, "value": tag}} for tag in query.hashtags]
    if users and query.terms:
        compound["should"] = [{"equals": {
            "path": "username", "value": " ".join(query.terms), "score": {"constant": {"value": 1000}},
        }}]
    order = {"score": {"$meta": "searchScore"}, "username": 1, "_id": 1} if users else (
        {"score": {"$meta": "searchScore"}, "published_at": -1, "_id": -1} if sort == "relevance"
        else {"published_at": -1, "_id": -1}
    )
    return {
        "index": USERS_INDEX if users else PUBLICATIONS_INDEX, "compound": compound, "sort": order,
        **({"searchAfter": after} if after else {}),
    }


def query_key(query: SearchQuery, users: bool, sort: SearchSort) -> str:
    """Fingerprint query semantics for continuation validation.

    :param query: Normalized search input.
    :param users: Whether the continuation belongs to user search.
    :param sort: Requested ordering.
    :return: A deterministic fingerprint including index version and search kind.
    """
    data = [INDEX_VERSION, users, sort, query.terms, query.hashtags]
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()


def encode_cursor(token: str, key: str) -> str:
    """Wrap an Atlas token in a versioned, query-bound cursor.

    :param token: Atlas searchSequenceToken for the last returned result.
    :param key: Fingerprint of the query, search kind, and ordering.
    :return: URL-safe opaque continuation text.
    """
    payload = json.dumps({"v": INDEX_VERSION, "key": key, "token": token}).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(value: str | None, key: str) -> str | None:
    """Reject malformed cursors or continuations from different query semantics.

    :param value: Opaque API cursor, or None for the first page.
    :param key: Expected query fingerprint.
    :return: The inner Atlas token, or None for an initial request.
    """
    if value is None:
        return None
    try:
        payload = json.loads(base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True))
        if (
            not isinstance(payload, dict) or payload.get("v") != INDEX_VERSION or payload.get("key") != key
            or not isinstance(payload.get("token"), str) or not payload["token"]
        ):
            raise ValueError("Cursor semantics differ")
        token = payload["token"]
        base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        return token
    except (ValueError, TypeError, UnicodeError) as exc:
        raise InvalidOperation("Invalid search cursor for this query and sort") from exc
