"""Versioned, explicitly provisioned Atlas Search index definitions."""

from typing import Any

from backend.search.query import PUBLICATIONS_INDEX, USERS_INDEX


def text_field(*, username: bool = False) -> list[dict[str, Any]]:
    """Define literal text and last-token prefix indexing without stemming.

    :param username: Whether to treat the whole ASCII handle as one autocomplete token.
    :return: String and autocomplete mappings with node-independent relevance scoring.
    """
    return [
        {"type": "string", "analyzer": "lucene.standard", "similarity": {"type": "stableTfl"}},
        {
            "type": "autocomplete", "analyzer": "username_lower" if username else "lucene.standard",
            "tokenization": "edgeGram", "minGrams": 2, "maxGrams": 64, "foldDiacritics": False,
            "similarity": {"type": "stableTfl"},
        },
    ]


INDEX_DEFINITIONS = {
    PUBLICATIONS_INDEX: ("search_publications", {"mappings": {"dynamic": False, "fields": {
        "_id": {"type": "objectId"}, "published_at": {"type": "date"},
        "title": text_field(), "text": text_field(), "hashtags": {"type": "token"},
    }}}),
    USERS_INDEX: ("users", {
        "analyzers": [{
            "name": "username_lower", "tokenizer": {"type": "keyword"},
            "tokenFilters": [{"type": "lowercase"}],
        }],
        "mappings": {"dynamic": False, "fields": {
            "_id": {"type": "objectId"},
            "username": [*text_field(username=True), {"type": "token", "normalizer": "lowercase"}],
            "display_name": text_field(), "bio": text_field(), "search_hashtags": {"type": "token"},
        }},
    }),
}
