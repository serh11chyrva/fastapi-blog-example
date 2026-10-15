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
REGISTER = {key: value for key, value in ACCOUNT.items() if key != "id"} | {"password": PASSWORD}
LOGIN = {"identifier": ACCOUNT["email"], "password": PASSWORD}
SESSION = {
    "id": "68eb734d21a0f8956be4c302",
    "created_at": "2026-10-12T08:42:19Z",
    "last_seen_at": "2026-10-14T07:18:46Z",
    "expires_at": "2026-11-11T08:42:19Z",
    "ip_address": "192.0.2.47",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
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
}
BADGE = {
    "version": 2,
    "code": "early-adopter",
    "payload": {
        "label": "Early adopter",
        "description": "Joined Commonplace during its first community release.",
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
PROFILE = {
    "id": ACCOUNT["id"],
    "username": ACCOUNT["username"],
    **{key: value for key, value in PROFILE_UPDATE.items() if key != "revision"},
    "links": [LINK_RESPONSE],
    "avatar_url": AVATAR_URL,
    "badges": [BADGE],
    "follower_count": 127,
    "following_count": 43,
    "is_following": False,
}
OWN_PROFILE = {**PROFILE, "revision": 0, "badges": [OWNER_BADGE]}
PROFILE_USER = {
    "id": "68eb7491d37a2f06b8ce9540",
    "username": "elliot_gray",
    "display_name": "Elliot Gray",
    "avatar_url": "/static/images/avatars/d10c7629ab3e4f85a79160b2f8c4e035.jpg",
}
AUTHOR = {
    "author_id": ACCOUNT["id"],
    "author_username": ACCOUNT["username"],
    "author_display_name": ACCOUNT["display_name"],
    "author_avatar_url": AVATAR_URL,
}
POST_TEXT = "Finished a 24 km ride along the river before breakfast. The best debugging ideas always seem to arrive away from the keyboard."
POST_CREATE = {"text": POST_TEXT}
POST = {
    "id": "68eb856f7a02c1349de6b580",
    "kind": "micro_post",
    "share_url": "/@maya_bennett/finished-a-24-km-ride-along-the-river-before-breakfast-the-best--a98f7c1326e44b6a8c5d39e27104bf60",
    "text": POST_TEXT,
    "images": [],
    **AUTHOR,
    "created_at": "2026-10-12T10:03:27Z",
    "updated_at": "2026-10-12T10:03:27Z",
}
POST_IMAGE_URL = "/static/images/post-images/74b936dfe1a24c708951c3e628a0fd5b.jpg"
POST_WITH_IMAGES = POST | {"images": [POST_IMAGE_URL], "updated_at": "2026-10-12T10:06:14Z"}
ARTICLE_BODY = {
    "type": "doc",
    "content": [
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Make room for ten minutes"}]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "I started leaving a paperback next to the coffee machine. "},
            {"type": "text", "text": "Ten pages before opening my laptop", "marks": [{"type": "bold"}]},
            {"type": "text", "text": " turned out to be a habit I could keep, even on busy weekdays."},
        ]},
    ],
}
ARTICLE_CREATE = {
    "title": "A reading habit that fits into a busy week",
    "summary": "How a paperback by the coffee machine helped me read twelve books in six months.",
    "body": ARTICLE_BODY,
}
ARTICLE_UPDATE = ARTICLE_CREATE | {"title": "Ten pages before the first meeting"}
ARTICLE = {
    "id": "68ebb250c39a6184f027de93",
    "kind": "article",
    "share_url": "/@maya_bennett/a-reading-habit-that-fits-into-a-busy-week--c7412d809e364a5bb18762f90d3ea458",
    **ARTICLE_CREATE,
    "thumbnail_url": None,
    "inline_image_urls": [],
    "status": "draft",
    **AUTHOR,
    "created_at": "2026-10-12T13:14:08Z",
    "updated_at": "2026-10-12T13:14:08Z",
    "scheduled_at": None,
    "published_at": None,
}
THUMBNAIL_URL = "/static/images/article-covers/65c924eb1f8d4a36b2907d83ef6a015c.jpg"
ARTICLE_PUBLISHED = ARTICLE | {
    "status": "published",
    "thumbnail_url": THUMBNAIL_URL,
    "updated_at": "2026-10-13T09:26:41Z",
    "published_at": "2026-10-13T09:26:41Z",
}
ARTICLE_UPDATED = ARTICLE | ARTICLE_UPDATE | {
    "share_url": "/@maya_bennett/ten-pages-before-the-first-meeting--c7412d809e364a5bb18762f90d3ea458",
    "updated_at": "2026-10-12T14:08:33Z",
}
PUBLISH_AT = (datetime.now(UTC) + timedelta(days=7)).replace(hour=9, minute=30, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
ARTICLE_SCHEDULE = {"publish_at": PUBLISH_AT}
ARTICLE_SCHEDULED = ARTICLE | {"status": "scheduled", "scheduled_at": PUBLISH_AT, "updated_at": "2026-10-14T07:18:46Z"}
ARTICLE_IMAGE = {
    "url": "/static/images/article-images/e815d392a60b4f78b129c3470dea6952.webp",
    "alt_text": "Paperback and coffee on a wooden desk.webp",
}
FEED_ARTICLE = {key: ARTICLE_PUBLISHED[key] for key in (
    "id", "kind", "share_url", "title", "summary", "thumbnail_url",
    "author_id", "author_username", "author_display_name", "author_avatar_url", "published_at",
)} | {"text": None, "images": []}
FEED_POST = {key: POST[key] for key in (
    "id", "kind", "share_url", "text", "images", "author_id", "author_username", "author_display_name", "author_avatar_url",
)} | {"title": None, "summary": None, "thumbnail_url": None, "published_at": POST["created_at"]}
CURSOR = base64.urlsafe_b64encode(json.dumps({
    "time": FEED_POST["published_at"], "kind": FEED_POST["kind"], "id": FEED_POST["id"],
}, separators=(",", ":")).encode()).decode().rstrip("=")
FEED = {"items": [FEED_ARTICLE, FEED_POST], "next_cursor": CURSOR}
