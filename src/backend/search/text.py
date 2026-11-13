"""Extract complete article text without indexing attachment metadata."""

import re
from typing import Any

from backend.publications.hashtags import extract_hashtags, normalize_tag


def article_content(document: dict[str, Any]) -> tuple[str, list[str]]:
    """Read full article text and tags, preserving words split by formatting marks.

    Code remains searchable text but does not create hashtags. Existing links and
    URLs do not create tags. Formula sources are excluded. Structured hashtag nodes contribute their visible text.

    :param document: Validated TipTap document, never modified by extraction.
    :return: Normalized full text and sorted unique normalized hashtags.
    """
    structured_tags: set[str] = set()

    def visit(node: dict[str, Any], tags_allowed: bool = True) -> tuple[str, str]:
        """Read one node with separate searchable and tag-bearing text.

        :param node: Validated node within the document.
        :param tags_allowed: Whether the containing node permits hashtag recognition.
        :return: Searchable text and text eligible for hashtag recognition.
        """
        kind = node.get("type")
        if kind == "text":
            text = node.get("text", "")
            excluded = any(mark.get("type") in {"code", "link"} for mark in node.get("marks", []))
            return text, text if tags_allowed and not excluded else " "
        if kind == "hashtag" or (kind == "attachment" and node.get("attrs", {}).get("type") == "hashtag"):
            tag = str(node.get("attrs", {}).get("tag", ""))
            if tags_allowed:
                structured_tags.add(normalize_tag(tag))
            return "#" + tag, " "
        if kind in {"hardBreak", "horizontalRule"}:
            return " ", " "
        if kind in {"image", "attachment", "mention", "blockMath"}:
            return " ", " "
        children = [visit(child, tags_allowed and kind != "codeBlock") for child in node.get("content", [])]
        separator = "" if kind in {"paragraph", "heading", "codeBlock"} else " "
        return separator.join(text for text, _ in children), separator.join(text for _, text in children)

    text, tag_text = visit(document)
    return " ".join(text.split()), sorted(set(extract_hashtags(tag_text)) | structured_tags)


def article_excerpt(text: str, terms: tuple[str, ...]) -> str | None:
    """Select a current-text passage near a literal or prefix match.

    :param text: Full text extracted from the currently visible source article.
    :param terms: Normalized query words or exact tags, without a leading hash.
    :return: A passage of up to 280 characters with context ellipses, or None for the standard preview.
    """
    positions = [match.start() for term in terms if (match := re.search(re.escape(term), text, re.IGNORECASE))]
    if not positions:
        return None
    start = max(0, min(positions) - 80)
    if start:
        boundary = text.find(" ", start, start + 30)
        if boundary >= 0:
            start = boundary + 1
    end = min(len(text), start + 276)
    return ("… " if start else "") + text[start:end].strip() + (" …" if end < len(text) else "")
