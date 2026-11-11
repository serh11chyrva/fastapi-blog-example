"""Derive article previews from saved document text."""

from backend.articles.validation import ArticleBody


def article_summary(document: ArticleBody) -> str:
    """Extract the first 280 characters of normalized text in document order.

    Inline formatting does not introduce spaces inside words. Block boundaries and
    hard breaks separate text; media attributes and other metadata are excluded.

    :param document: Validated article body to summarize.
    :return: At most 280 Unicode characters, or an empty string for a textless body.
    """
    fragments: list[str] = []
    pending: list[object] = [document]

    while pending:
        node = pending.pop()
        if isinstance(node, str):
            fragments.append(node)
            continue
        if not isinstance(node, dict):
            continue

        kind = node.get("type")
        if kind == "text":
            fragments.append(str(node.get("text", "")))
        elif kind == "hardBreak":
            fragments.append(" ")
        else:
            children = node.get("content", [])
            if isinstance(children, list):
                pending.append(" ")
                pending.extend(reversed(children))

    return " ".join("".join(fragments).split())[:280]
