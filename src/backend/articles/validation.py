"""Validate the supported TipTap tree before storing or traversing editor data."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError

from backend.links.platforms import validate_link_url
from backend.publications.attachments import PublicationAttachment

type ArticleBody = dict[str, JsonValue]
type NodeKind = Literal[
    "doc",
    "paragraph",
    "heading",
    "text",
    "bulletList",
    "orderedList",
    "listItem",
    "blockquote",
    "codeBlock",
    "hardBreak",
    "horizontalRule",
    "image",
    "attachment",
    "mention",
    "hashtag",
]
MAX_ARTICLE_JSON_BYTES = 1_000_000
MAX_ARTICLE_DEPTH = 64
MAX_ARTICLE_NODES = 10_000
IMAGE_SOURCE = re.compile(r"/static/images/article-images/([0-9a-f]{32}\.(?:jpg|png|webp))")
BLOCK_NODES = {
    "paragraph",
    "heading",
    "bulletList",
    "orderedList",
    "blockquote",
    "codeBlock",
    "horizontalRule",
    "image",
    "attachment",
}
ATTACHMENT_ADAPTER = TypeAdapter(PublicationAttachment)


class TiptapMark(BaseModel):
    """Supported inline formatting mark and its strictly typed attributes."""

    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["bold", "italic", "strike", "code", "link"]
    attrs: dict[str, JsonValue] = Field(default_factory=dict)


class TiptapNode(BaseModel):
    """Typed node shape; parent-child rules are checked separately."""

    model_config = ConfigDict(extra="forbid", strict=True)

    type: NodeKind
    attrs: dict[str, JsonValue] = Field(default_factory=dict)
    marks: list[TiptapMark] = Field(default_factory=list)
    content: list[TiptapNode] = Field(default_factory=list)
    text: str | None = None


def _bound_tree(document: ArticleBody) -> None:
    """Reject malformed or oversized trees before recursive model parsing.

    :param document: TipTap JSON document to validate or traverse.
    :return: None.
    """
    pending: list[tuple[object, int]] = [(document, 0)]
    count = 0

    while pending:
        value, depth = pending.pop()
        count += 1

        if depth > MAX_ARTICLE_DEPTH or count > MAX_ARTICLE_NODES:
            raise ValueError("Article exceeds 64 levels or 10,000 content nodes")

        if not isinstance(value, dict):
            raise ValueError("Content nodes must be objects")

        children = value.get("content", [])

        if not isinstance(children, list):
            raise ValueError("Node content must be an array")

        if count + len(pending) + len(children) > MAX_ARTICLE_NODES:
            raise ValueError("Article exceeds 10,000 content nodes")

        pending.extend((child, depth + 1) for child in children)


def validate_tiptap_document(document: ArticleBody) -> None:
    """Reject malformed shapes and unsupported editor structures with ValueError.

    Depth and node limits are checked before recursive model parsing. Validation
    retains the original JSON. Image ownership is checked during article updates.

    :param document: TipTap JSON document to validate or traverse.
    :return: None.
    """
    _bound_tree(document)

    try:
        root = TiptapNode.model_validate(document)
    except ValidationError as exc:
        raise ValueError("Article contains malformed or unsupported content nodes or marks") from exc

    if root.type != "doc":
        raise ValueError("Article body must be a TipTap document")

    try:
        encoded = json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError("Article body must contain valid UTF-8 JSON") from exc

    if len(encoded) > MAX_ARTICLE_JSON_BYTES:
        raise ValueError("Article content is too large")

    pending = [root]

    while pending:
        node = pending.pop()
        children = {child.type for child in node.content}

        if node.type in {"doc", "blockquote", "listItem"}:
            if not node.content or not children.issubset(BLOCK_NODES):
                raise ValueError("Document, quote, and list item nodes require block content")

            if node.type == "listItem" and node.content[0].type != "paragraph":
                raise ValueError("List items must start with a paragraph")
        elif node.type in {"bulletList", "orderedList"}:
            if not node.content or children != {"listItem"}:
                raise ValueError("Lists must contain list items")
        elif node.type in {"paragraph", "heading"}:
            if not children.issubset({"text", "hardBreak", "mention", "hashtag"}):
                raise ValueError("Paragraphs and headings require inline content")
        elif node.type == "codeBlock":
            if not children.issubset({"text"}) or any(child.marks for child in node.content):
                raise ValueError("Code blocks accept unmarked text only")
        elif node.content:
            raise ValueError("Leaf nodes cannot contain child content")

        if node.type == "text":
            if not node.text:
                raise ValueError("Text nodes must contain nonempty text")
        elif node.text is not None:
            raise ValueError("Only text nodes may contain text")

        if node.marks and node.type not in {"text", "hardBreak"}:
            raise ValueError("Marks apply only to inline content")

        if node.type == "heading":
            level = node.attrs.get("level", 1)

            if type(level) is not int or level not in {1, 2, 3}:
                raise ValueError("Only heading levels 1 through 3 are supported")

        if node.type == "orderedList":
            start = node.attrs.get("start", 1)

            if type(start) is not int or start < 1:
                raise ValueError("Ordered list start must be a positive integer")

        if node.type == "image":
            src = node.attrs.get("src")

            if not isinstance(src, str) or not IMAGE_SOURCE.fullmatch(src):
                raise ValueError("Article images must use uploaded article media")

            for attribute in ("alt", "title"):
                value = node.attrs.get(attribute)

                if value is not None and not isinstance(value, str):
                    raise ValueError("Image alternate text and title must be strings")

        for mark in node.marks:
            if mark.type == "link":
                href = mark.attrs.get("href")

                if not isinstance(href, str):
                    raise ValueError("Article links must contain a URL")

                validate_link_url(href)

        pending.extend(node.content)

    article_body_attachments(document)


def article_body_attachments(document: ArticleBody) -> list[PublicationAttachment]:
    """Validate and extract typed descriptors from structurally validated editor content.

    Block attachment attributes contain a complete descriptor including its type. Inline mention
    and hashtag attributes omit type because the node already supplies it. At most 30 descriptors
    may appear in a body; ordinary image nodes retain their separate image ownership rules.

    :param document: TipTap document whose node shapes, depth, and parent-child rules were validated.
    :return: Typed body descriptors in document order, without modifying the original JSON.
    """
    attachments: list[PublicationAttachment] = []
    pending: list[ArticleBody] = [document]

    while pending:
        node = pending.pop()
        kind = node.get("type")

        if kind in {"attachment", "mention", "hashtag"}:
            attrs = node.get("attrs", {})

            if not isinstance(attrs, dict):
                raise ValueError("Attachment attributes must be an object")

            if kind != "attachment":
                if "type" in attrs:
                    raise ValueError("Inline attachment attributes must omit type")

                attrs = {**attrs, "type": kind}

            try:
                attachments.append(ATTACHMENT_ADAPTER.validate_python(attrs))
            except ValidationError as exc:
                raise ValueError("Article contains invalid attachment attributes") from exc

            if len(attachments) > 30:
                raise ValueError("An article body can contain up to 30 typed attachments")

        children = node.get("content", [])

        if isinstance(children, list):
            pending.extend(child for child in reversed(children) if isinstance(child, dict))

    return attachments


def article_image_keys(document: ArticleBody) -> set[str]:
    """Extract image keys from a document that has passed body validation.

    :param document: TipTap JSON document to validate or traverse.
    :return: The unique stored object keys referenced by inline images.
    """
    found: set[str] = set()
    pending: list[ArticleBody] = [document]

    while pending:
        node = pending.pop()
        attrs = node.get("attrs")

        if node.get("type") == "image" and isinstance(attrs, dict):
            src = attrs.get("src")
            match = IMAGE_SOURCE.fullmatch(src) if isinstance(src, str) else None

            if match:
                found.add(f"article-images/{match.group(1)}")

        children = node.get("content", [])

        if isinstance(children, list):
            pending.extend(child for child in children if isinstance(child, dict))

    return found
