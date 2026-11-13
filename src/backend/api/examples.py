"""Consistent fictional data used by API schemas and the interactive reference."""

import base64
import json
from datetime import UTC, datetime, timedelta

ACCOUNT = {
    "id": "68eb731ab54f7c2a9130e6d8",
    "email": "maya.bennett@example.com",
    "username": "maya_bennett",
    "display_name": "Maya Bennett",
}
PASSWORD = "Cedar!Notebook73River"
REGISTER = {key: value for key, value in ACCOUNT.items() if key != "id"} | {
    "password": PASSWORD,
    "client_type": "web",
}
LOGIN = {"identifier": ACCOUNT["email"], "password": PASSWORD, "client_type": "web"}
SESSION = {
    "id": "68eb734d21a0f8956be4c302",
    "created_at": "2026-10-12T08:42:19Z",
    "last_seen_at": "2026-10-14T07:18:46Z",
    "expires_at": "2026-11-11T08:42:19Z",
    "client_type": "web",
    "location": "Kyiv, Ukraine",
    "device": "Chrome 141.0.0 on Windows 10",
    "current": True,
}
LINK = {"label": "Reading journal", "url": "https://maya.example.com/journal"}
LINK_RESPONSE = {
    **LINK,
    "version": 1,
    "id": "da3861fe-4336-411f-8e34-e32d37c2ebad",
    "platform": "website",
    "redirect_url": "/api/v1/links/da3861fe-4336-411f-8e34-e32d37c2ebad/redirect",
}
PROFILE_UPDATE = {
    "revision": 0,
    "display_name": ACCOUNT["display_name"],
    "bio": "Software engineer, weekend cyclist, and collector of good reading recommendations.",
    "links": [LINK],
    "location": "Kyiv, Ukraine",
}
BADGE = {
    "version": 2,
    "code": "early-adopter",
    "payload": {
        "label": "Early adopter",
        "description": "Joined the blog during its first community release.",
        "background_color": "#f3f4f6",
        "text_color": "#374151",
        "icon_url": "/static/images/badges/star.svg",
        "icon_color": "#374151",
    },
}
OWNER_BADGE = {
    **BADGE,
    "assigned_at": "2026-10-12T08:42:19Z",
    "preferences": {"enabled": True},
    "permissions": {"can_disable": True},
}
AVATAR_URL = "/static/images/avatars/9a47dc2e381f4b60a75d2c8b613e09af.webp"
AUTHENTICATED_ACCOUNT = ACCOUNT | {"avatars": {"original": AVATAR_URL}}
PROFILE = {
    "id": ACCOUNT["id"],
    "username": ACCOUNT["username"],
    **{key: value for key, value in PROFILE_UPDATE.items() if key != "revision"},
    "links": [LINK_RESPONSE],
    "avatars": {"original": AVATAR_URL},
    "badges": [BADGE],
    "joined_at": "2026-10-12T08:42:19Z",
    "posts_count": 12,
    "banner_url": "/static/images/profile-banners/96b1d2efb94446b2b891eb516cdbe4c0.webp",
    "follower_count": 127,
    "following_count": 43,
    "is_following": False,
}
OWN_PROFILE = {**PROFILE, "revision": 0, "badges": [OWNER_BADGE]}
PROFILE_USER = {
    "id": "68eb7491d37a2f06b8ce9540",
    "username": "elliot_gray",
    "display_name": "Elliot Gray",
    "avatars": {"original": "/static/images/avatars/d10c7629ab3e4f85a79160b2f8c4e035.jpg"},
}
AUTHOR = {
    "id": ACCOUNT["id"],
    "username": ACCOUNT["username"],
    "display_name": ACCOUNT["display_name"],
    "avatars": {"original": AVATAR_URL},
}
POST_TEXT = "Finished a 24 km ride along the river before breakfast. The best debugging ideas always seem to arrive away from the keyboard."
POST_CREATE = {"text": POST_TEXT}
POST = {
    "id": "68eb856f7a02c1349de6b580",
    "kind": "micro_post",
    "share_url": "/@maya_bennett/finished-a-24-km-ride-along-the-river-before-breakfast-the-best--a98f7c1326e44b6a8c5d39e27104bf60",
    "text": POST_TEXT,
    "attachments": [],
    "link_resolutions": {},
    "reply": None,
    "pending": False,
    "read_only": False,
    "archived_at": None,
    "pinned_at": None,
    "owner_id": ACCOUNT["id"],
    "authors": [AUTHOR],
    "created_at": "2026-10-12T10:03:27Z",
    "updated_at": "2026-10-12T10:03:27Z",
}
POST_WITH_FEATURED_AUTHORS = POST | {"authors": [AUTHOR, PROFILE_USER]}
POST_IMAGE_URL = "/static/images/post-images/74b936dfe1a24c708951c3e628a0fd5b.jpg"
POST_WITH_IMAGES = POST | {
    "attachments": [{"type": "image", "url": POST_IMAGE_URL, "alt": ""}],
    "updated_at": "2026-10-12T10:06:14Z",
}
POST_WITH_GIF = POST | {
    "attachments": [{
        "type": "gif",
        "url": "/static/images/post-images/74b936dfe1a24c708951c3e628a0fd5b.gif",
        "alt": "An animated landscape",
    }],
}
GIF_UPLOAD_REQUEST = {
    "files": [{"filename": "animation.gif", "content_type": "image/gif", "size_bytes": 8388608}],
}
GIF_UPLOAD_RESPONSE = {
    "upload_id": "65f0c2a1b2c3d4e5f6071899",
    "expires_at": "2026-10-14T12:10:00Z",
    "files": [{
        "upload_url": (
            "http://localhost:3900/blog-publications/temporary/0123456789abcdef0123456789abcdef"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=example"
        ),
        "method": "PUT",
        "headers": {"Content-Type": "image/gif"},
        "max_size_bytes": 8388608,
    }],
}
ARTICLE_BODY = {
    "type": "doc",
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Make room for ten minutes"}],
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "I started leaving a paperback next to the coffee machine. ",
                },
                {
                    "type": "text",
                    "text": "Ten pages before opening my laptop",
                    "marks": [{"type": "bold"}],
                },
                {
                    "type": "text",
                    "text": " turned out to be a habit I could keep, even on busy weekdays.",
                },
            ],
        },
    ],
}
ARTICLE_CREATE = {
    "title": "A reading habit that fits into a busy week",
    "body": ARTICLE_BODY,
    "hero_layout": "cover_title",
    "comments_enabled": True,
}
ARTICLE_UPDATE = ARTICLE_CREATE | {"title": "Ten pages before the first meeting", "hero_layout": "title_cover"}
ARTICLE = {
    "id": "68ebb250c39a6184f027de93",
    "kind": "article",
    "share_url": "/@maya_bennett/a-reading-habit-that-fits-into-a-busy-week--c7412d809e364a5bb18762f90d3ea458",
    **ARTICLE_CREATE,
    "summary": ("Make room for ten minutes I started leaving a paperback next to the coffee machine. "
                "Ten pages before opening my laptop turned out to be a habit I could keep, even on busy weekdays."),
    "thumbnail_url": None,
    "inline_image_urls": [],
    "attachments": [],
    "link_resolutions": {},
    "status": "draft",
    "read_only": True,
    "archived_at": None,
    "pinned_at": None,
    "owner_id": ACCOUNT["id"],
    "authors": [AUTHOR],
    "created_at": "2026-10-12T13:14:08Z",
    "updated_at": "2026-10-12T13:14:08Z",
    "scheduled_at": None,
    "published_at": None,
}
ARTICLE_WITH_FEATURED_AUTHORS = ARTICLE | {"authors": [AUTHOR, PROFILE_USER]}
THUMBNAIL_URL = "/static/images/article-covers/65c924eb1f8d4a36b2907d83ef6a015c.jpg"
ARTICLE_PUBLISHED = ARTICLE | {
    "status": "published",
    "read_only": False,
    "thumbnail_url": THUMBNAIL_URL,
    "updated_at": "2026-10-13T09:26:41Z",
    "published_at": "2026-10-13T09:26:41Z",
}
ARTICLE_COMMENTS_DISABLED = ARTICLE_PUBLISHED | {"comments_enabled": False}
POST_RICH_CREATE = {
    "text": "Reading notes worth continuing.",
    "attachments": [{
        "type": "og_card", "url": "https://example.com/notes", "title": "Reading notes",
        "description": "A few ideas to revisit.",
    }],
}
LINK_CARD = POST_RICH_CREATE["attachments"][0] | {
    "image_url": "https://example.com/notes-cover.jpg", "site_name": "Example",
}
POST_WITH_CONTENT = POST | POST_RICH_CREATE | {
    "link_resolutions": {"https://example.com/notes": {
        "status": "ready", "card": LINK_CARD, "attachment": LINK_CARD, "player_url": None,
    }},
}
ARTICLE_RICH_CREATE = ARTICLE_CREATE | {
    "body": {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Discussed with "},
                    {"type": "mention", "attrs": {"user_id": PROFILE_USER["id"]}},
                    {"type": "text", "text": " "},
                    {"type": "hashtag", "attrs": {"tag": "reading"}},
                    {"type": "text", "text": "1", "marks": [{"type": "superscript"}]},
                ],
            },
            {
                "type": "attachment",
                "attrs": {
                    "type": "embed",
                    "provider": "spotify",
                    "url": "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
                },
            },
            {"type": "blockMath", "attrs": {"latex": "E = mc^2"}},
        ],
    },
}
ARTICLE_WITH_CONTENT = ARTICLE | ARTICLE_RICH_CREATE | {"summary": "Discussed with 1"}
ARTICLE_UPDATED = (
    ARTICLE
    | ARTICLE_UPDATE
    | {
        "share_url": "/@maya_bennett/ten-pages-before-the-first-meeting--c7412d809e364a5bb18762f90d3ea458",
        "updated_at": "2026-10-12T14:08:33Z",
    }
)
PUBLISH_AT = (
    (datetime.now(UTC) + timedelta(days=7))
    .replace(hour=9, minute=30, second=0, microsecond=0)
    .isoformat()
    .replace("+00:00", "Z")
)
ARTICLE_SCHEDULE = {"publish_at": PUBLISH_AT}
ARTICLE_SCHEDULED = ARTICLE | {
    "status": "scheduled",
    "scheduled_at": PUBLISH_AT,
    "updated_at": "2026-10-14T07:18:46Z",
}
ARTICLE_IMAGE = {
    "url": "/static/images/article-images/e815d392a60b4f78b129c3470dea6952.webp",
    "alt_text": "Paperback and coffee on a wooden desk.webp",
}
FEED_ARTICLE = {
    key: ARTICLE_PUBLISHED[key]
    for key in (
        "id",
        "kind",
        "share_url",
        "title",
        "summary",
        "thumbnail_url",
        "comments_enabled",
        "owner_id",
        "authors",
        "attachments",
        "link_resolutions",
        "read_only",
        "archived_at",
        "pinned_at",
        "published_at",
        "updated_at",
    )
} | {"text": None}
FEED_POST = {
    key: POST[key]
    for key in (
        "id",
        "kind",
        "share_url",
        "text",
        "attachments",
        "link_resolutions",
        "read_only",
        "archived_at",
        "pinned_at",
        "owner_id",
        "authors",
        "updated_at",
    )
} | {
    "title": None,
    "summary": None,
    "thumbnail_url": None,
    "published_at": POST["created_at"],
}
FEED_REPOST = {
    "id": "68ebd31ff2b7a8c901234560",
    "kind": "repost",
    "reposted_by": PROFILE_USER,
    "published_at": "2026-10-14T10:00:00Z",
    "post": FEED_POST,
}
CURSOR = (
    base64.urlsafe_b64encode(
        json.dumps(
            {
                "version": 2,
                "time": FEED_POST["published_at"],
                "kind": FEED_POST["kind"],
                "id": FEED_POST["id"],
            },
            separators=(",", ":"),
        ).encode()
    )
    .decode()
    .rstrip("=")
)
FEED = {"items": [FEED_REPOST, FEED_ARTICLE, FEED_POST], "next_cursor": CURSOR}
REPOST_PAGE = {"items": [FEED_REPOST], "next_cursor": None}
POST_INTERACTIONS = {
    "likes_count": 12, "comments_count": 3, "reposts_count": 1,
    "liked": True, "saved": False, "reposted": False,
}
ARTICLE_INTERACTIONS = {
    "likes_count": 8, "comments_count": 2, "reposts_count": None,
    "liked": False, "saved": True, "reposted": None,
}
COMMENT_CREATE = {"text": "This is a useful way to think about it."}
POST_REPLY_CREATE = COMMENT_CREATE | {"parent_id": None}
POST_REPLY = {
    "id": "68ebd420f2b7a8c901234561",
    "author": PROFILE_USER,
    "text": COMMENT_CREATE["text"],
    "created_at": "2026-10-14T10:05:00Z",
    "updated_at": "2026-10-14T10:05:00Z",
    "deleted": False,
    "likes_count": 4,
    "liked": True,
    "post_id": POST["id"],
    "parent_id": None,
    "root_id": "68ebd420f2b7a8c901234561",
    "depth": 0,
    "replies_count": 1,
}
POST_REPLY_CHILD = POST_REPLY | {
    "id": "68ebd421f2b7a8c901234562", "text": "Agreed, especially the practical example.",
    "parent_id": POST_REPLY["id"], "depth": 1, "replies_count": 0, "likes_count": 0, "liked": False,
}
POST_REPLY_DELETED = POST_REPLY | {
    "author": None, "text": None, "deleted": True, "likes_count": 0, "liked": False,
}
ARTICLE_COMMENT = {
    "id": "68ebd422f2b7a8c901234563",
    "author": PROFILE_USER,
    "text": COMMENT_CREATE["text"],
    "created_at": "2026-10-14T10:05:00Z",
    "updated_at": "2026-10-14T10:05:00Z",
    "deleted": False,
    "likes_count": 4,
    "liked": True,
    "article_id": ARTICLE["id"],
    "post_id": None,
    "parent_id": None,
    "root_id": "68ebd422f2b7a8c901234563",
    "depth": 0,
    "replies_count": 0,
}
for reply_example in (POST_REPLY, POST_REPLY_CHILD, ARTICLE_COMMENT):
    reply_example["publication"] = POST | {
        "id": reply_example["id"], "text": reply_example["text"],
        "share_url": None, "owner_id": PROFILE_USER["id"], "authors": [PROFILE_USER],
        "created_at": reply_example["created_at"], "updated_at": reply_example["updated_at"],
        "reply": {
            "kind": "article" if reply_example.get("article_id") else "micro_post",
            "publication_id": reply_example.get("article_id") or reply_example["post_id"],
            "parent_id": reply_example["parent_id"], "root_id": reply_example["root_id"],
            "depth": reply_example["depth"],
        },
    }
POST_REPLY_DELETED["publication"] = None
THREAD_PART = FEED_POST | {
    "id": POST_REPLY["id"], "text": POST_REPLY["text"], "reply": POST_REPLY["publication"]["reply"],
    "share_url": None, "published_at": POST_REPLY["created_at"], "updated_at": POST_REPLY["updated_at"],
}
THREAD_PREVIEW = {"parts": [THREAD_PART], "has_more": False}
AUTHOR_THREAD_PAGE = {"root": FEED_POST, "items": [THREAD_PART], "next_cursor": None}
POST_REPLY_PAGE = {"items": [POST_REPLY], "next_cursor": None}
ARTICLE_COMMENT_PAGE = {"items": [ARTICLE_COMMENT], "next_cursor": None}
ARTICLE_PREVIEW = {
    key: FEED_ARTICLE[key]
    for key in ("kind", "id", "share_url", "authors", "title", "summary", "thumbnail_url", "published_at")
}
POST_PREVIEW = {
    key: FEED_POST[key]
    for key in ("kind", "id", "share_url", "authors", "text", "thumbnail_url", "published_at", "updated_at")
}
PROFILE_TIMELINE = {"items": [FEED_REPOST, FEED_POST], "next_cursor": None}
SAVED_PAGE = {
    "items": [{
        "id": "68ebd423f2b7a8c901234564", "saved_at": "2026-10-14T10:10:00Z", "publication": FEED_ARTICLE,
    }],
    "next_cursor": None,
}

# Archive and pin operations preserve the publication's content timestamps.
POST_ARCHIVED = POST | {"archived_at": "2026-11-12T09:00:00Z", "pinned_at": None, "read_only": True}
POST_PINNED = POST | {"archived_at": None, "pinned_at": "2026-11-12T09:05:00Z"}
ARTICLE_ARCHIVED = ARTICLE_PUBLISHED | {
    "archived_at": "2026-11-12T09:10:00Z", "pinned_at": None, "read_only": True,
}
ARCHIVE_PAGE = {
    "items": [
        FEED_ARTICLE | {"archived_at": ARTICLE_ARCHIVED["archived_at"], "pinned_at": None, "read_only": True},
        FEED_POST | {"archived_at": POST_ARCHIVED["archived_at"], "pinned_at": None, "read_only": True},
    ],
    "next_cursor": None,
}
PROFILE_PINS = [FEED_POST | {"pinned_at": POST_PINNED["pinned_at"]}]

SEARCH_USERS_PAGE = {"items": [PROFILE_USER | {"bio": "Building small tools with #python."}], "next_cursor": None}
SEARCH_PUBLICATIONS_PAGE = {
    "items": [{"publication": FEED_ARTICLE, "excerpt": "A passage from the current article body about FastAPI."}],
    "next_cursor": None,
}
