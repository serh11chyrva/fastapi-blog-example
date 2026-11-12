"""Recognize Unicode hashtags consistently in saved content and search queries."""

import re
import unicodedata

URL_PATTERN = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


def hashtag_character(value: str) -> bool:
    """Identify a Unicode letter, number, combining mark, or underscore.

    :param value: One character from the original text.
    :return: Whether the character may belong to a hashtag.
    """
    return value == "_" or unicodedata.category(value)[0] in {"L", "N", "M"}


def normalize_tag(value: str) -> str:
    """Normalize a tag for exact, case-insensitive comparison.

    :param value: Tag text without a leading hash.
    :return: NFC-normalized, case-folded tag text.
    """
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", value).casefold())


def validate_tag(value: str) -> str:
    """Validate the spelling and length of a structured hashtag.

    :param value: Original tag spelling without a leading hash.
    :return: Original spelling, preserving the author's presentation.
    """
    if not 1 <= len(value) <= 64 or not all(hashtag_character(character) for character in value):
        raise ValueError("Use 1 to 64 Unicode letters, numbers, combining marks, or underscores for a hashtag")
    return value


def hashtag_spans(text: str, *, max_length: int | None = 64) -> list[tuple[int, int, str]]:
    """Locate complete hashtags outside HTTP URLs without changing text offsets.

    :param text: Untrusted plain text in its original spelling.
    :param max_length: Maximum tag length, or None when the caller needs to reject oversized query tags explicitly.
    :return: Start, exclusive end, and original tag spelling for each valid hashtag.
    """
    urls = [match.span() for match in URL_PATTERN.finditer(text)]
    url_index = 0
    spans = []
    for start, character in enumerate(text):
        if character != "#" or (
            start and (hashtag_character(text[start - 1]) or text[start - 1] == "#")
        ):
            continue
        while url_index < len(urls) and urls[url_index][1] <= start:
            url_index += 1
        if url_index < len(urls) and urls[url_index][0] <= start < urls[url_index][1]:
            continue
        end = start + 1
        while end < len(text) and hashtag_character(text[end]):
            end += 1
        tag = text[start + 1:end]
        if tag and (max_length is None or len(tag) <= max_length):
            spans.append((start, end, tag))
    return spans


def extract_hashtags(text: str) -> list[str]:
    """Extract unique normalized hashtags from plain text.

    :param text: Visible text, excluding rich-text code and existing links when appropriate.
    :return: Sorted normalized tags suitable for exact indexing.
    """
    return sorted({normalize_tag(tag) for _, _, tag in hashtag_spans(text)})
