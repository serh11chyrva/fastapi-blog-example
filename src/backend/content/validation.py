from typing import Any
from urllib.parse import urlsplit


ALLOWED_NODES = {"doc", "paragraph", "heading", "text", "bulletList", "orderedList", "listItem", "blockquote", "codeBlock", "hardBreak", "horizontalRule"}
ALLOWED_MARKS = {"bold", "italic", "strike", "code", "link"}
MAX_ARTICLE_JSON_BYTES = 1_000_000


def validate_tiptap_document(document: dict[str, Any]) -> None:
    import json

    if len(json.dumps(document, ensure_ascii=False).encode()) > MAX_ARTICLE_JSON_BYTES:
        raise ValueError("Article content is too large")
    if document.get("type") != "doc" or not isinstance(document.get("content", []), list):
        raise ValueError("Article body must be a TipTap document")

    def visit(node: dict[str, Any]) -> None:
        if not isinstance(node, dict) or node.get("type") not in ALLOWED_NODES:
            raise ValueError("Article contains an unsupported content node")
        if node["type"] == "text" and not isinstance(node.get("text"), str):
            raise ValueError("Text nodes must contain text")
        if node["type"] == "heading":
            level = (node.get("attrs") or {}).get("level", 1)
            if level not in {1, 2, 3}:
                raise ValueError("Only heading levels 1 through 3 are supported")
        for mark in node.get("marks", []):
            if not isinstance(mark, dict) or mark.get("type") not in ALLOWED_MARKS:
                raise ValueError("Article contains an unsupported text mark")
            if mark.get("type") == "link":
                href = (mark.get("attrs") or {}).get("href", "")
                parsed = urlsplit(href)
                if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                    raise ValueError("Article links must use http or https")
        for child in node.get("content", []):
            visit(child)

    for child in document.get("content", []):
        visit(child)
