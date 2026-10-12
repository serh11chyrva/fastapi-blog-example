# Commonplace API reference

This guide documents the implemented API in addition to the interactive OpenAPI UI at `http://localhost:8080/api/docs` and its machine-readable schema at `/api/openapi.json`.

## Conventions

- Base path: `/api/v1`.
- JSON is used unless an endpoint accepts a multipart upload.
- Timestamps are ISO 8601 UTC strings. IDs are MongoDB ObjectId strings.
- Authentication is a server-side session delivered in the `blog_session` HttpOnly cookie. The raw token is never part of a JSON response. The cookie defaults to `SameSite=Lax`; `Secure` is configurable.
- Keep the cookie between requests. For browser requests use same-origin `fetch` with `credentials: "same-origin"`. All POST, PUT, PATCH, and DELETE requests must include the configured `APP_ORIGIN` in the `Origin` header. This is enforced as a CSRF defense.
- Successful deletes, logout, follow, and unfollow return `204 No Content` with an empty body.
- Validation errors return `422` with FastAPI's `{ "detail": [...] }` shape. Unauthenticated protected calls return `401`; missing or inaccessible objects generally return `404`.
- Rate limits: registration is limited to 5 attempts per email per hour; login is limited to 8 attempts per identifier per 10 minutes. Limits are enforced per client IP and per normalized identity. A limit response is `429`.

For command-line examples below, set `BASE=http://localhost:8080` and use a cookie jar. Replace example secrets with local demo values as appropriate.

## Authentication and sessions

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public | Create account and session |
| POST | `/auth/login` | Public | Log in by email or username |
| GET | `/auth/me` | Session | Get current account |
| GET | `/auth/sessions` | Session | List active sessions with IP and User-Agent |
| DELETE | `/auth/sessions/{session_id}` | Session | Revoke one of your sessions |
| POST | `/auth/sessions/logout-others` | Session | Revoke every session except current |
| POST | `/auth/logout` | Session | Revoke current session and clear cookie |

Registration request:

```json
{
  "email": "reader@example.com",
  "username": "reader_one",
  "display_name": "Avery Reader",
  "password": "Correct-Horse-Battery-42"
}
```

The username accepts 3–24 ASCII letters, digits, or underscores; an optional leading `@` is removed and the value is normalized to lowercase. Email is normalized to lowercase. Passwords must contain 12–256 characters. A successful response is `201 Created` and sets the session cookie:

```json
{
  "id": "65f0c2a1b2c3d4e5f6071829",
  "email": "reader@example.com",
  "username": "reader_one",
  "display_name": "Avery Reader"
}
```

If the email or username is already used, registration returns `409 Conflict`. The password is never returned.

```sh
curl -i -c cookies.txt -H "Origin: $BASE" -H "Content-Type: application/json" \
  -d '{"email":"reader@example.com","username":"reader_one","display_name":"Avery Reader","password":"Correct-Horse-Battery-42"}' \
  "$BASE/api/v1/auth/register"
```

Login request supports either identifier form:

```json
{"identifier":"reader@example.com","password":"Correct-Horse-Battery-42"}
```

```json
{"identifier":"@reader_one","password":"Correct-Horse-Battery-42"}
```

An invalid login returns `401` with `{"detail":"Invalid username/email or password"}`. Example:

```sh
curl -i -c cookies.txt -H "Origin: $BASE" -H "Content-Type: application/json" \
  -d '{"identifier":"reader_one","password":"Correct-Horse-Battery-42"}' \
  "$BASE/api/v1/auth/login"
```

Session list response:

```json
[
  {
    "id": "65f0c2a1b2c3d4e5f6071830",
    "created_at": "2026-10-12T09:30:00Z",
    "last_seen_at": "2026-10-12T09:34:15Z",
    "expires_at": "2026-11-11T09:30:00Z",
    "ip_address": "127.0.0.1",
    "user_agent": "Mozilla/5.0 Example Browser",
    "current": true
  }
]
```

The session ID can be passed to `DELETE /auth/sessions/{session_id}`. Other users' session IDs are concealed as `404`. `/auth/sessions/logout-others` and `/auth/logout` return `204`.

## Profiles and follows

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/users/{username}` | Public | Read profile |
| GET | `/users/{username}/publications?kind=all` | Public | List up to 50 public publications |
| PATCH | `/me/profile` | Session | Update own profile |
| PUT | `/me/avatar` | Session | Upload JPEG, PNG, or WebP avatar |
| GET | `/media/avatars/{object_name}` | Public | Read avatar image bytes |
| GET | `/users/{username}/followers` | Public | List followers |
| GET | `/users/{username}/following` | Public | List followed accounts |
| PUT | `/users/{username}/follow` | Session | Follow account (idempotent) |
| DELETE | `/users/{username}/follow` | Session | Unfollow account (idempotent) |

Profile update is a partial JSON object. Omitted fields are unchanged. `display_name` is limited to 64 characters, `bio` to 280, and `links` to eight HTTP(S) entries. Send an empty array to clear links; `null` does not clear a field.

```json
{
  "display_name": "Avery R.",
  "bio": "Writing about books and software.",
  "links": [
    {"label": "Website", "url": "https://example.com"},
    {"label": "GitHub", "url": "https://github.com/reader-one"}
  ]
}
```

Profile response example:

```json
{
  "id": "65f0c2a1b2c3d4e5f6071829",
  "username": "reader_one",
  "display_name": "Avery R.",
  "bio": "Writing about books and software.",
  "links": [{"label":"Website","url":"https://example.com"}],
  "avatar_url": "/api/v1/media/avatars/0123456789abcdef0123456789abcdef.png",
  "badges": [{"code":"early-reader","label":"Early Reader","description":"Joined the demo community early.","assigned_at":"2026-10-12T09:30:00Z"}],
  "follower_count": 3,
  "following_count": 5,
  "is_following": false
}
```

Avatar uploads use `multipart/form-data` with the field name `file`. The default maximum is 5 MiB. Unsupported formats return `415`; oversized files return `413`.

## Publication images

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| PUT | `/posts/{post_id}/images` | Session, post owner | Replace a post's image gallery (one to five files) |
| POST | `/articles/{article_id}/images` | Session, article owner | Upload an image for insertion in the TipTap body |
| PUT | `/articles/{article_id}/thumbnail` | Session, article owner | Replace the article cover image |
| GET | `/media/post-images/{object_name}` | Public | Read an image attached to a public post |
| GET | `/media/article-images/{object_name}` | Public or draft owner | Read an inline article image |
| GET | `/media/article-thumbnails/{object_name}` | Public or draft owner | Read an article cover image |

Uploads use `multipart/form-data`: use the `files` field for post galleries and `file` for article images and thumbnails. Gallery uploads replace the complete gallery. Post and inline article images are limited to 5 MiB each and JPEG, PNG, or WebP; posts accept up to five files and articles up to 30 inline images. The thumbnail limit is 10 MiB. Media endpoints only serve objects still attached to an accessible publication.

Example post with three images:

```sh
curl -i -b cookies.txt -H "Origin: $BASE" \
  -F "files=@cover.jpg" -F "files=@detail.png" -F "files=@sketch.webp" \
  "$BASE/api/v1/posts/65f0c2a1b2c3d4e5f6071829/images"
```

Create an article draft first, then upload an inline image. The response URL can be inserted in the article TipTap JSON as an `image` node. Article JSON only permits uploaded same-origin article media URLs; the image must have been uploaded to that article before saving the body.

```sh
curl -i -b cookies.txt -H "Origin: $BASE" -F "file=@figure.png" \
  "$BASE/api/v1/articles/65f0c2a1b2c3d4e5f6071829/images"
```

The response is `{ "url": "/api/v1/media/article-images/<object>.png", "alt_text": "figure.png" }`.

```sh
curl -i -b cookies.txt -H "Origin: $BASE" \
  -F "file=@avatar.png;type=image/png" "$BASE/api/v1/me/avatar"
```

Following yourself returns `400`. Repeated follow/unfollow requests are safe and return `204`.

## Feeds

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/feeds/public?kind=all&limit=20` | Public | Chronological mixed feed |
| GET | `/feeds/following?kind=all&limit=20` | Session | Chronological feed from followed accounts |

`kind` is `all`, `micro_post`, or `article`. `limit` is 1–50 (default 20). When `next_cursor` is non-null, pass it unchanged as the next `cursor` query parameter. Do not construct or edit cursors.

```json
{
  "items": [
    {
      "id": "65f0c2a1b2c3d4e5f6071831",
      "kind": "micro_post",
      "title": null,
      "text": "A small idea worth sharing.",
      "summary": null,
      "author_id": "65f0c2a1b2c3d4e5f6071829",
      "author_username": "reader_one",
      "author_display_name": "Avery R.",
      "author_avatar_url": null,
      "published_at": "2026-10-12T09:34:15Z"
    },
    {
      "id": "65f0c2a1b2c3d4e5f6071832",
      "kind": "article",
      "title": "Notes on reading",
      "text": null,
      "summary": "A few practical ideas.",
      "author_id": "65f0c2a1b2c3d4e5f6071829",
      "author_username": "reader_one",
      "author_display_name": "Avery R.",
      "author_avatar_url": null,
      "published_at": "2026-10-12T09:30:00Z"
    }
  ],
  "next_cursor": null
}
```

## Micro-posts

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/posts` | Session | Publish immediately |
| GET | `/posts/{post_id}` | Public | Read post |
| PATCH | `/posts/{post_id}` | Author | Replace post text |
| DELETE | `/posts/{post_id}` | Author | Soft-delete post |
| GET | `/publications/{username}/{share_slug}` | Public | Resolve a shared `@username/slug--share-id` link |

Create request and representative response:

```json
{"text":"A small idea worth sharing with the community."}
```

```json
{
  "id":"65f0c2a1b2c3d4e5f6071831",
  "kind":"micro_post",
  "text":"A small idea worth sharing with the community.",
  "author_id":"65f0c2a1b2c3d4e5f6071829",
  "author_username":"reader_one",
  "author_display_name":"Avery R.",
  "author_avatar_url":null,
  "created_at":"2026-10-12T09:34:15Z",
  "updated_at":"2026-10-12T09:34:15Z"
}
```

Text must contain 1–280 non-whitespace characters. `PATCH` accepts the same complete request shape. A missing, deleted, or non-owned post returns `404` for edit/delete.

## Articles

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/articles` | Session | Create a draft |
| GET | `/me/articles?status=all` | Session | List own articles |
| GET | `/articles/{article_id}` | Public / author for draft | Read article |
| PATCH | `/articles/{article_id}` | Author | Partially update article |
| POST | `/articles/{article_id}/publish` | Author | Publish draft |
| POST | `/articles/{article_id}/schedule` | Author | Schedule a future publication |
| POST | `/articles/{article_id}/draft` | Author | Return an article to draft |
| DELETE | `/articles/{article_id}` | Author | Soft-delete article |
| PUT | `/articles/{article_id}/thumbnail` | Author | Upload JPEG, PNG, or WebP thumbnail |

Create an article as a draft, then edit or publish it. `status` for the author list is `all`, `draft`, `scheduled`, or `published`. A draft request body uses TipTap JSON, not HTML. Supported nodes/marks are document, paragraph, heading levels 1–3, text, hard break, horizontal rule, bullet/ordered list, list item, blockquote, code block, bold, italic, strike, code, and HTTP(S) links. The JSON document is limited to 1,000,000 encoded bytes.

Upload an optional thumbnail using multipart field `file` at `PUT /articles/{article_id}/thumbnail` (JPEG, PNG, or WebP; 10 MiB maximum by default). A published thumbnail is public; while an article is a draft or scheduled, only its author can retrieve the image. Set a future ISO 8601 timestamp with timezone to schedule publication:

```json
{"publish_at":"2026-10-13T09:00:00Z"}
```

The scheduler checks every 15 seconds. Returning to draft clears a pending schedule or unpublishes an article. Deleting an article soft-deletes it and removes it from public feeds.

```json
{
  "title": "Notes on building a reading habit",
  "summary": "A few practical ideas for making time to read.",
  "body": {
    "type": "doc",
    "content": [
      {"type":"heading","attrs":{"level":2},"content":[{"type":"text","text":"Start small"}]},
      {"type":"paragraph","content":[{"type":"text","text":"Ten minutes a day is enough to begin."}]},
      {"type":"bulletList","content":[{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"Keep a book nearby"}]}]}]}
    ]
  }
}
```

Article response adds `id`, `kind: "article"`, `status`, author fields, `created_at`, `updated_at`, and nullable `published_at`. `PATCH` accepts any subset of `title`, `summary`, and `body`. Published articles are publicly readable. Draft reads by anyone except the author return `404`.

## Health and error envelope

`GET /health` returns `{"status":"ok","database":"ok","redis":"ok","object_storage":"ok"}` when all dependencies answer; otherwise it returns `503`.

Application errors use a `detail` string, for example:

```json
{"detail":"Authentication required"}
```

Validation errors use FastAPI's structured list:

```json
{
  "detail": [
    {"type":"string_too_long","loc":["body","text"],"msg":"String should have at most 280 characters","input":"..."}
  ]
}
```
