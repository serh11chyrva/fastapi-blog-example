"""Varied publication fixtures covering supported editor nodes and typed attachments."""

from datetime import datetime, timedelta

from backend.articles.models import Article
from backend.articles.schemas import ArticleCreate
from backend.articles.validation import ArticleBody
from backend.core.config import get_settings
from backend.core.resources import AppResources
from backend.demo.common import demo_id, insert_fixture
from backend.demo.media import ensure_image
from backend.posts.models import MicroPost
from backend.posts.schemas import MicroPostCreate
from backend.profiles.models import User
from backend.publications.attachments import (
    ArticleAttachment,
    EmbedAttachment,
    HashtagAttachment,
    ImageAttachment,
    LinkAttachment,
    MentionAttachment,
    OpenGraphAttachment,
    PostAttachment,
)
from backend.storage.urls import publication_image_url

POST_TOPICS = [
    "A good writing habit starts with one small note and a little patience.",
    "A keyboard-only tour is a surprisingly effective way to find interface problems.",
    "I left an hour unscheduled today and finally finished the paragraph I was avoiding.",
    "Small releases turn assumptions into useful feedback.",
    "A quiet park, a notebook, and no notifications: a very good afternoon.",
    "The best documentation explains what happens when a request fails.",
    "A book recommendation is often an invitation to a longer conversation.",
]


PLAYER_RESOURCES = [
    ("soundcloud", "https://soundcloud.com/forss/flickermood"),
    ("spotify", "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"),
    ("youtube", "https://www.youtube.com/watch?v=aqz-KE-bpKQ"),
    ("vimeo", "https://vimeo.com/76979871"),
]


def paragraph(value: str) -> ArticleBody:
    """Build a plain paragraph in the supported editor format.

    :param value: Text displayed inside the paragraph.
    :return: A paragraph node containing one text node.
    """
    return {"type": "paragraph", "content": [{"type": "text", "text": value}]}


def article_body(
    title: str, mention_id: str, image_urls: list[str], reference_id: str | None, *, showcase: bool = False,
) -> ArticleBody:
    """Assemble a rich document covering the supported formatting and attachment nodes.

    :param title: Story-specific introduction.
    :param mention_id: Existing public account mentioned inline.
    :param image_urls: Images owned by this article and available as inline nodes.
    :param reference_id: Optional published article referenced by a block attachment.
    :param showcase: Whether to include the dedicated rich link and player examples.
    :return: A TipTap-compatible document for validation by ArticleCreate.
    """
    nodes = [
        {"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": "A place to begin"}]},
        paragraph(f"{title}. Try saving a draft, adding a reference, and returning to the discussion later."),
        {"type": "paragraph", "attrs": {"textAlign": "center"}, "content": [
            {"type": "text", "text": "Thoughtful ", "marks": [{"type": "bold"}]},
            {"type": "text", "text": "small ", "marks": [{"type": "italic"}]},
            {"type": "text", "text": "imperfect ", "marks": [{"type": "strike"}]},
            {"type": "text", "text": "steps", "marks": [{"type": "code"}]},
            {"type": "text", "text": " make room for revisions.", "marks": [{"type": "underline"}]},
            {"type": "hardBreak"},
            {"type": "text", "text": "Read the Python tutorial", "marks": [
                {"type": "link", "attrs": {"href": "https://docs.python.org/3/tutorial/"}}
            ]},
        ]},
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "A short checklist"}]},
        {"type": "bulletList", "content": [
            {"type": "listItem", "content": [paragraph("Start with a clear question.")]},
            {"type": "listItem", "content": [paragraph("Share a concrete example.")]},
        ]},
        {"type": "orderedList", "attrs": {"start": 3}, "content": [
            {"type": "listItem", "content": [paragraph("Read the first draft aloud.")]},
            {"type": "listItem", "content": [paragraph("Leave room for reader feedback.")]},
        ]},
        {"type": "blockquote", "attrs": {"citation": "Notes from the publishing workbench"},
         "content": [paragraph("Clarity usually arrives through revision.")]},
        {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "A tiny experiment"}]},
        {"type": "codeBlock", "attrs": {"language": "python"}, "content": [
            {"type": "text", "text": "def greet(reader):\n    return f'Hello, {reader}!'\n"}
        ]},
        {"type": "horizontalRule"},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "A conversation with "},
            {"type": "mention", "attrs": {"user_id": mention_id}},
            {"type": "text", "text": " about "},
            {"type": "hashtag", "attrs": {"tag": "SmallSteps"}},
            {"type": "text", "text": "."},
        ]},
    ]
    nodes.extend(
        {"type": "image", "attrs": {"src": url, "alt": f"Geometric landscape {index + 1}", "title": None}}
        for index, url in enumerate(image_urls)
    )
    nodes.append({
        "type": "attachment",
        "attrs": {"type": "link", "url": "https://developer.mozilla.org/", "label": "Keep exploring"},
    })
    if showcase:
        nodes.append({
            "type": "attachment",
            "attrs": {
                "type": "og_card", "url": "https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout",
                "title": "CSS grid layout", "description": "A reference for laying out rows and columns.",
                "site_name": "MDN Web Docs",
            },
        })
        nodes.extend(
            {"type": "attachment", "attrs": {"type": "embed", "provider": provider, "url": url}}
            for provider, url in PLAYER_RESOURCES
        )
    if reference_id:
        nodes.append({"type": "attachment", "attrs": {"type": "article", "article_id": reference_id}})

    return {"type": "doc", "content": nodes}


async def seed_publications(
    resources: AppResources, users: dict[str, User], now: datetime,
) -> tuple[dict[str, MicroPost], dict[str, Article]]:
    """Insert varied, stable publications while preserving previously edited or deleted fixtures.

    :param resources: Database and object-storage infrastructure.
    :param users: Existing demo accounts indexed by username.
    :param now: Timezone-aware run timestamp used only for newly created fixtures.
    :return: Demo posts and articles indexed by fixture names.
    """
    articles: dict[str, Article] = {}
    stories = [
        ("reading-room", "alice", "A reading room for small ideas", "published"),
        ("field-guide", "ben", "A field guide to calm software", "published"),
        ("first-draft", "casey", "The useful mess of a first draft", "published"),
        ("accessible-design", "dana", "Designing for a patient reader", "published"),
        ("city-walk", "elena", "What a slow city walk can teach us", "published"),
        ("tiny-experiments", "farah", "Learning through tiny experiments", "published"),
        ("weekend-notes", "alice", "Notes from an unplanned weekend", "published"),
        ("release-checklist", "ben", "A small release checklist", "published"),
        ("private-notebook", "alice", "Private notebook: an unfinished idea", "draft"),
        ("draft-workbench", "ben", "Private workbench: the next project", "draft"),
        ("tomorrow-letter", "alice", "A letter scheduled for tomorrow", "scheduled"),
        ("next-week", "ben", "The next chapter, scheduled ahead", "scheduled"),
        ("publishing-workbench", "alice", "Notes from the publishing workbench", "published"),
    ]
    reference_id = None

    for index, (key, username, title, status) in enumerate(stories):
        showcase = key == "publishing-workbench"
        resource_id = demo_id("article", index)
        existing = await Article.get(resource_id)

        if existing is not None:
            articles[key] = existing
        else:
            cover = await ensure_image(resources, "article-covers", key, index)
            inline_keys = [
                await ensure_image(resources, "article-images", f"{key}-{image}", index + image)
                for image in range(2 if index == 0 else 1)
            ]
            body = article_body(
                title, str(users["dana"].id),
                [publication_image_url(image, "article-images") for image in inline_keys], reference_id,
                showcase=showcase,
            )
            payload = ArticleCreate(title=title, summary=f"A practical story about {title.lower()}.", body=body)
            created_at = now - timedelta(days=3, hours=index)
            published_at = now - timedelta(minutes=25 if showcase else 20 + index * 75) if status == "published" else None
            updated_at = published_at + timedelta(minutes=5) if showcase and published_at else created_at
            article = Article(
                id=resource_id, owner_id=users[username].id,
                featured_author_ids=[users["dana"].id, users["farah"].id] if index == 0 else [],
                title=payload.title, summary=payload.summary, body=payload.body,
                thumbnail_key=cover, inline_image_keys=inline_keys, status=status,
                attachments=[HashtagAttachment(tag="FieldNotes"), LinkAttachment(url="https://docs.python.org/3/")],
                created_at=created_at, updated_at=updated_at,
                published_at=published_at,
                scheduled_at=now + timedelta(days=1 if index == 10 else 7) if status == "scheduled" else None,
            )
            await insert_fixture(resources, article, users[username].id, "article")
            articles[key] = article

        if index == 0 and articles[key].status == "published" and articles[key].deleted_at is None:
            reference_id = str(resource_id)

    posts: dict[str, MicroPost] = {}
    writers = ["alice", "ben", "casey", "dana", "elena", "farah"]
    for index in range(37):
        key = f"note-{index:02d}"
        resource_id = demo_id("post", index)
        existing = await MicroPost.get(resource_id)

        if existing is not None:
            posts[key] = existing
            continue

        username = {35: "alice", 36: "dana"}.get(index, writers[index % len(writers)])
        attachments = [
            HashtagAttachment(tag="FieldNotes"),
            MentionAttachment(user_id=str(users[writers[(index + 1) % len(writers)]].id)),
        ]
        image_keys = []

        if index in {0, 1, 6, 12}:
            image_keys = [
                await ensure_image(resources, "post-images", f"{key}-{image}", index + image)
                for image in range(5 if index == 1 else 1)
            ]
            attachments += [
                ImageAttachment(url=publication_image_url(image, "post-images"), alt=f"Landscape study {number + 1}")
                for number, image in enumerate(image_keys)
            ]

        if index == 0:
            attachments += [
                LinkAttachment(url="https://developer.mozilla.org/", label="Documentation worth reading"),
                OpenGraphAttachment(
                    url="https://docs.python.org/3/", title="A small guide to Python",
                    description="Caller-supplied preview metadata with a locally generated illustration.",
                    image_url=get_settings().app_origin + publication_image_url(image_keys[0], "post-images"),
                    site_name="FastAPI Blog Example demo",
                ),
            ]
            if reference_id:
                attachments.append(ArticleAttachment(article_id=reference_id))

        if 2 <= index <= 5:
            provider, url = PLAYER_RESOURCES[index - 2]
            attachments.append(EmbedAttachment(provider=provider, url=url))

        text = f"Field note {index + 1:02d}: {POST_TOPICS[index % len(POST_TOPICS)]}"
        created_at = now - timedelta(minutes=40 + index * 35)
        if index == 35:
            text = "I keep a short checklist before publishing. Leaving an example here for the next draft."
            workbench = articles["publishing-workbench"]
            if workbench.status == "published" and workbench.deleted_at is None:
                attachments.append(ArticleAttachment(article_id=str(workbench.id)))
            created_at = now - timedelta(minutes=14)
        if index == 36:
            text = "A small note worth returning to. The examples are often where a conversation begins."
            original = posts["note-00"] if posts["note-00"].deleted_at is None else posts["note-35"]
            if original.deleted_at is None:
                attachments.append(PostAttachment(post_id=str(original.id)))
            created_at = now - timedelta(minutes=12)

        payload = MicroPostCreate(text=text, attachments=attachments)
        post = MicroPost(
            id=resource_id, owner_id=users[username].id,
            featured_author_ids=[users["elena"].id] if index == 1 else [],
            text=payload.text, attachments=payload.attachments, image_keys=image_keys,
            created_at=created_at, updated_at=created_at,
        )
        await insert_fixture(resources, post, users[username].id, "micro_post")
        posts[key] = post

    return posts, articles
