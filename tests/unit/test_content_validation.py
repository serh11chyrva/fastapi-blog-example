import pytest
from pydantic import ValidationError

from backend.content.schemas import ArticleCreate, MicroPostCreate
from backend.content.validation import validate_tiptap_document


def test_micro_post_is_trimmed_and_limited_to_280_characters() -> None:
    assert MicroPostCreate(text="  hello  ").text == "hello"
    with pytest.raises(ValidationError):
        MicroPostCreate(text="x" * 281)
    with pytest.raises(ValidationError):
        MicroPostCreate(text="   ")


def test_tiptap_document_accepts_supported_content() -> None:
    document = {
        "type": "doc",
        "content": [
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Hello"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "A safe link", "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}]}]},
        ],
    }
    validate_tiptap_document(document)
    assert ArticleCreate(title="Story", body=document).title == "Story"


@pytest.mark.parametrize(
    "document",
    [
        {"type": "doc", "content": [{"type": "image", "attrs": {"src": "javascript:alert(1)"}}]},
        {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Click", "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}]}]}]},
        {"type": "doc", "content": [{"type": "heading", "attrs": {"level": 6}, "content": [{"type": "text", "text": "Unsupported"}]}]},
    ],
)
def test_tiptap_document_rejects_unsupported_or_unsafe_content(document: dict) -> None:
    with pytest.raises(ValueError):
        validate_tiptap_document(document)
