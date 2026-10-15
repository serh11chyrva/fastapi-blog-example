# Commonplace API reference

This guide documents the implemented API in addition to the interactive Scalar reference at `http://localhost:8080/api/docs` and its machine-readable schema at `/api/openapi.json`. Endpoint metadata is declared beside each route; required cookie security is generated from authentication dependencies, and optional-session reads explicitly allow anonymous access.

## Conventions

- Upload size limits are defined in `src/backend/core/config.py`: 5 MiB per avatar, post image, or inline article image, and 10 MiB per article thumbnail. These limits are not configured through environment variables.
- Base path: `/api/v1`.
- Application API requests use JSON. Presigned Garage PUT requests send raw file bytes without application cookies.
- Timestamps are ISO 8601 UTC strings. Account and document IDs are MongoDB ObjectId strings; profile link IDs are UUID strings.
- Authentication is a server-side session delivered in the `blog_session` HttpOnly cookie. The raw token is never part of a JSON response. The cookie defaults to `SameSite=Lax`; `Secure` is configurable.
- Keep the cookie between application API requests. Use same-origin `fetch` with `credentials: "same-origin"`. All POST, PUT, PATCH, and DELETE requests under `/api/v1` must include the configured `APP_ORIGIN` in the `Origin` header as a CSRF defense. Presigned Garage PUT requests use `credentials: "omit"` and the returned headers; browser access is controlled by storage CORS.
- Successful deletes, logout, follow, and unfollow return `204 No Content` with an empty body.
- Concurrent audited writes can return `409`; reload the affected resource and reconcile changes before retrying. Transaction bodies are not automatically replayed. Database failures return `503`; an uncertain commit may have succeeded, so reload before retrying.
- Validation errors return `422` with FastAPI's `{ "detail": [...] }` shape. Unauthenticated protected calls return `401`; missing or inaccessible objects generally return `404`.
- Rate limits: registration is limited to 5 attempts per email per hour; login is limited to 8 attempts per identifier per 10 minutes. Limits are enforced per client IP and per normalized identity. Counters and their expiry are updated atomically; existing counters missing an expiry are repaired. A limit response is `429`.

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
| GET | `/users/{username}` | Public | Read public profile with visible badges only |
| GET | `/me/profile` | Session | Read own profile, revision, and all badge assignments |
| PATCH | `/me/profile` | Session | Update own profile using its expected revision |
| PATCH | `/me/badges/{code}` | Session | Change own badge visibility using the expected revision |
| GET | `/links/{link_id}/redirect` | Public | Temporarily redirect to a saved link |
| GET | `/users/{username}/links/{link_id}/redirect` | Public | Deprecated compatibility redirect |
| GET | `/users/{username}/publications?kind=all` | Public | List up to 50 public publications |
| POST | `/me/avatar/uploads` | Session | Prepare an avatar upload |
| POST | `/me/avatar/uploads/{upload_id}/complete` | Session | Confirm and replace avatar; return current own profile |
| GET | `/users/{username}/followers` | Public | List followers |
| GET | `/users/{username}/following` | Public | List followed accounts |
| PUT | `/users/{username}/follow` | Session | Follow account (idempotent) |
| DELETE | `/users/{username}/follow` | Session | Unfollow account (idempotent) |

### Profile edits and concurrency

Read `GET /me/profile` before editing and send its `revision` with every profile or badge visibility PATCH. Revision is an optimistic concurrency counter, independent of data format `version`. Every successful PATCH increments it, including no-op updates; avatar attachment increments it once as well. Stale revisions or concurrent transactional writes return `409` with `{"detail":"Profile changed; reload your profile before saving"}`. Reload and explicitly reconcile edits before retrying; do not automatically resubmit an old form with a new revision. Missing revision returns `422`, including for older clients.

Editable fields are partial: omitted or null values stay unchanged. `display_name` is trimmed, nonblank, and limited to 64 characters, `bio` to 280, and `links` to eight entries. Labels are trimmed and allow 1–32 characters; URLs allow 8–500 characters and require absolute HTTP(S) URLs with a hostname, without credentials, whitespace, control characters, or backslashes. The same link validation applies to persistence models. Use `[]` to clear links. Unknown top-level profile fields return `422`.

```json
{
  "revision": 0,
  "display_name": "Avery R.",
  "bio": "Writing about books and software.",
  "links": [
    {"label": "Website", "url": "https://example.com"},
    {"label": "GitHub", "url": "https://github.com/reader-one"}
  ]
}
```

PATCH returns the own-profile schema and new revision. Own-profile GET, profile PATCH, badge PATCH, and avatar confirmation use `Cache-Control: private, no-store`. Private data is available only for the requesting account through `/me`; signing in does not expose another owner's settings.

Public profile example:

```json
{
  "id": "65f0c2a1b2c3d4e5f6071829",
  "username": "reader_one",
  "display_name": "Avery R.",
  "bio": "Writing about books and software.",
  "links": [{"version":1,"id":"da3861fe-4336-411f-8e34-e32d37c2ebad","label":"Website","url":"https://example.com","platform":"website","redirect_url":"/api/v1/links/da3861fe-4336-411f-8e34-e32d37c2ebad/redirect"}],
  "avatar_url": "/static/images/avatars/0123456789abcdef0123456789abcdef.png",
  "badges": [{"version":2,"code":"early-reader","payload":{"label":"Early Reader","description":"Joined the demo community early.","background_color":"#f3f4f6","text_color":"#374151","icon_url":"/static/images/badges/star.svg","icon_color":"#374151"}}],
  "follower_count": 3,
  "following_count": 5,
  "is_following": false
}
```

`GET /me/profile` returns the same profile fields plus `revision`; its `badges` includes hidden assignments and adds private fields to each entry:

```json
{
  "version": 2,
  "code": "early-reader",
  "payload": {
    "label": "Early Reader",
    "description": "Joined the demo community early.",
    "background_color": "#f3f4f6",
    "text_color": "#374151",
    "icon_url": "/static/images/badges/star.svg",
    "icon_color": "#374151"
  },
  "assigned_at": "2026-10-12T09:30:00Z",
  "preferences": {"enabled": true},
  "permissions": {"can_disable": true}
}
```

### Stable links and redirects

Links retain format `version: 1`; input defaults to 1 when omitted, and unsupported versions return `422`. Format version describes the wire shape, not edit history. Retain an existing `id` when changing destination or reordering. Without an ID (or with null), the server reuses an unclaimed existing link with the exact same URL, even when its label changes. Multiple possible matches return `422` and require an explicit ID. An unmatched URL creates a UUID. Explicit IDs are reserved before URL matching; duplicate or foreign IDs return `422`. Removing a link makes its redirect return `404`. An edited URL without its original ID represents a new link.

`platform` is an icon-ready identifier: `github`, `gitlab`, `x`, `facebook`, `instagram`, `threads`, `linkedin`, `youtube`, `tiktok`, `telegram`, `discord`, `reddit`, `twitch`, `medium`, `substack`, `pinterest`, `soundcloud`, `bandcamp`, `spotify`, `apple_music`, `behance`, `itch_io`, `kick`, `artstation`, `dribbble`, `deviantart`, `vimeo`, `patreon`, or `ko_fi`. Unrecognized domains use `website`. Matching is case-insensitive and uses the hostname and its subdomains, including aliases such as `twitter.com`, `youtu.be`, `t.me`, and `spotify.link`; paths and query strings do not affect detection. Creator subdomains such as `artist.bandcamp.com` and `studio.itch.io` are recognized. Apple Music matches `music.apple.com`, rather than all Apple websites. Lookalikes such as `github.com.example.org` are not GitHub. Self-hosted or custom-domain services use `website` unless their host is explicitly registered. VK, Stack Overflow, and Bluesky URLs remain valid links but use `website`.

Open `redirect_url` as a browser navigation rather than fetching JSON. `GET /links/{link_id}/redirect` returns `302 Found`, the saved destination in `Location`, and `Cache-Control: no-store`. It requires no session. Unknown or removed IDs return `404`; malformed UUIDs return `422`. The destination's query and fragment are retained, and endpoint query parameters are ignored. No UTM tagging or click counting is implemented; resolution is centralized in `backend.links.service.LinkService`. Future analytics failures should not prevent navigation.

New redirect addresses do not contain a profile handle. The previous `/users/{username}/links/{link_id}/redirect` path remains a deprecated compatibility alias, requiring that the named profile owns the ID. Links remain embedded in users with an index on `links.id`; a separate collection is not needed yet. `platform` and `redirect_url` are server-derived output fields.

### Badge definitions and visibility

Badge format `version: 2` moves every display field into `payload`. This is a breaking change from badge version 1: clients must use `payload.label` and `payload.description`. Public profiles filter hidden assignments on the server and never return their codes, assignment timestamps, visibility preferences, or permissions. The owner receives all assignments through `/me/profile`, including `preferences.enabled`, `permissions.can_disable`, and `assigned_at`.

Set visibility through `PATCH /me/badges/early-reader`:

```json
{"revision": 0, "enabled": false}
```

The response is the updated own profile with its new revision. The server enforces permission: disabling a mandatory badge returns `403`; re-enabling it is allowed. Unknown or unassigned codes return `404`. Unknown body fields and invalid/missing revision return `422`. A code occurs at most once per profile. Badge definitions, colors, and permissions are not editable through these owner endpoints.

Shared display payload and disable policy live in the `badge_definitions` collection, keyed by unique code. User assignments store only code, assignment time, and enabled state. Updating a definition updates every profile's display without copying changes into all users. Missing definitions return `503` instead of silently dropping assignments.

Payload colors are six-digit hex values. A null `icon_url` displays text only. A non-null `icon_color` renders the image as a monochrome CSS mask in that color; null preserves the image's original colors. Bundled SVG, PNG, and WebP assets are served publicly at `/static/images/badges/{icon_name}` with a one-hour cache, without Garage access. `star.svg` is supplied; unknown names return `404`. Add future assets under `src/backend/profiles/icons/` before assigning their URLs.

### Existing data

Startup runs an idempotent Beanie migration before serving requests. Existing link IDs are retained; older links without an ID receive the same deterministic UUID previously calculated from handle, original position, and URL, which is then persisted. Normal model validation no longer computes identities from mutable profile data. Users receive persisted revision 0 when absent and storage schema marker 2.

Legacy badge display fields and policy are promoted to definitions, and assignments retain code, timestamp, and enabled state. An existing definition wins; otherwise the first legacy assignment in user ObjectId order supplies the shared definition for that code. If historical copies differ, reconcile the resulting catalog before relying on those differences. Defaults preserve neutral colors and the star icon. Unsupported link versions or invalid legacy links fail migration rather than being silently discarded. New-format assignment writes are strictly validated.

Follower and following lists accept `offset` (default 0) and `limit` (default 20, maximum 100). Results keep descending follow time and ID order. Continue with offset plus the page size until a shorter page is returned. Concurrent follows/unfollows can shift offset pages; reload from offset 0 to refresh.

## Image uploads and downloads

Image uploads have three steps: prepare with JSON metadata, PUT raw bytes to the returned Garage URLs, then confirm. All preparation and confirmation routes require the resource owner's session and the application Origin header. Create the post or article draft before preparing its images. Preparation never changes attachments.

| Method | Path (under `/api/v1`) | Purpose |
| --- | --- | --- |
| POST | `/me/avatar/uploads` | Prepare one avatar |
| POST | `/me/avatar/uploads/{upload_id}/complete` | Confirm avatar; returns current own profile and revision |
| POST | `/posts/{post_id}/images/uploads` | Prepare one to five gallery images, in display order |
| POST | `/posts/{post_id}/images/uploads/{upload_id}/complete` | Replace the whole gallery; returns post |
| POST | `/articles/{article_id}/cover/uploads` | Prepare one cover |
| POST | `/articles/{article_id}/cover/uploads/{upload_id}/complete` | Replace cover; returns article with `thumbnail_url` |
| POST | `/articles/{article_id}/images/uploads` | Prepare one inline image |
| POST | `/articles/{article_id}/images/uploads/{upload_id}/complete` | Append inline image; returns `url` and `alt_text` |

JPEG, PNG, and WebP are accepted. Avatars, post images, and inline images allow 5 MiB; covers allow 10 MiB. Articles allow up to 30 inline images, checked again at confirmation. Files must be nonempty and their actual lengths must match the declared sizes. Signature checks reject unsupported bytes or bytes that disagree with the requested MIME type. Presigned PUT alone does not enforce the size limit: confirmation rejects oversized objects before attachment.

Preparation request:

```sh
curl -b cookies.txt -H "Origin: $BASE" -H "Content-Type: application/json" \
  -d '{"files":[{"filename":"figure.png","content_type":"image/png","size_bytes":1024}]}' \
  "$BASE/api/v1/articles/65f0c2a1b2c3d4e5f6071829/images/uploads"
```

Use the actual byte length of your local file. Example response (the URL's signature is illustrative):

```json
{
  "upload_id": "65f0c2a1b2c3d4e5f6071899",
  "expires_at": "2026-10-14T12:10:00Z",
  "files": [{
    "upload_url": "http://localhost:3900/blog-publications/temporary/0123456789abcdef0123456789abcdef?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=example",
    "method": "PUT",
    "headers": {"Content-Type": "image/png"},
    "max_size_bytes": 5242880
  }]
}
```

Upload each file to its corresponding returned URL with the returned headers. Do not send the application cookie, prepend `/api/v1`, or replace the signed host or path:

```sh
curl --fail -X PUT -H "Content-Type: image/png" --data-binary @figure.png "$UPLOAD_URL"
curl -b cookies.txt -H "Origin: $BASE" -X POST \
  "$BASE/api/v1/articles/65f0c2a1b2c3d4e5f6071829/images/uploads/$UPLOAD_ID/complete"
```

Confirmation has no request body. Its returned inline image can be inserted into this article's TipTap JSON:

```json
{"url":"/static/images/article-images/0123456789abcdef0123456789abcdef.png","alt_text":"figure.png"}
```

The server validates a separate final copy and attaches it in a transaction with the audit event. Replaying the temporary PUT cannot overwrite that final image. Repeating a completed confirmation does not attach again. Publication confirmations return the original saved result; avatar confirmation returns the current own profile and revision, including when replaying a completed upload from an older API format. A failed gallery confirmation leaves existing attachments intact. Concurrent edits can return `409`; retry confirmation while the upload is valid. If it expires, prepare a new upload.

Preparation and PUT URLs last ten minutes. Completion must start before the deadline and has a five-minute processing lease. Missing files, expired sessions, and concurrent confirmations return `409`; missing or inaccessible upload sessions return `404`. Oversized images return `413`, unsupported bytes return `415`, and size mismatch or count limits return `422`. Storage/database failures return `503`. Temporary files and abandoned final copies are queued for cleanup after an hour; replaced and deleted attachments are queued immediately. The worker runs every minute and retries failed deletions. Upload-session results are retained for seven days after expiry.

Downloads are at the application root, outside `/api/v1`:

| Method | Path | Access |
| --- | --- | --- |
| GET | `/static/images/avatars/{object_name}` | Public, attached avatar |
| GET | `/static/images/post-images/{object_name}` | Public, non-deleted post |
| GET | `/static/images/article-covers/{object_name}` | Published article or its author |
| GET | `/static/images/article-images/{object_name}` | Published article or its author |

Only attached images are served. Missing, deleted, or inaccessible images return `404`; unavailable storage returns `503`. Article images use `Cache-Control: private, no-store`, including published articles, so returning an article to draft does not leave a publicly cached copy. Avatars and post images use a one-hour public cache. TipTap image sources must use the new relative article-image paths and belong to the article being saved. Legacy multipart upload routes and `/api/v1/media/` download routes are removed, without migration or redirects.

Following yourself returns `400`. Repeated follow/unfollow requests are safe and return `204`.

## Feeds

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/feeds/public?kind=all&limit=20` | Public | Chronological mixed feed |
| GET | `/feeds/following?kind=all&limit=20` | Session | Chronological feed from followed accounts |

Feed items are a discriminated union: `micro_post` requires text, while `article` requires title and summary. The unused alternative fields remain null or empty for compatibility.

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

Create an article as a draft, then edit or publish it. `status` for the author list is `all`, `draft`, `scheduled`, or `published`. The author list accepts `offset` (default 0) and `limit` (default 20, maximum 100), ordered by updated time and ID descending. Request the next offset until fewer than limit entries are returned; there is no silent 100-article cutoff. Profile publication lists accept offset and limit too (default/maximum 50). Offset pagination can shift when publications are added or edited; refresh from offset 0 when reconciling changes. A draft request body uses TipTap JSON, not HTML. Supported nodes/marks are document, paragraph, heading levels 1–3, text, hard break, horizontal rule, bullet/ordered list, list item, blockquote, code block, bold, italic, strike, code, and HTTP(S) links. The JSON document is limited to 1,000,000 UTF-8 encoded bytes, 64 nesting levels, and 10,000 content nodes. Every node, attribute object, mark list, and child array is validated. Null child/mark arrays, unsupported nodes, and invalid parent-child structures return 422. Documents and blockquotes require block content; lists require list items; list items start with a paragraph.

Upload an optional cover through `/articles/{article_id}/cover/uploads` and its matching confirmation endpoint (JPEG, PNG, or WebP; 10 MiB maximum). A published thumbnail is public; while an article is a draft or scheduled, only its author can retrieve the image. Set a future ISO 8601 timestamp with timezone to schedule publication (replace the illustrative date with your intended future time):

```json
{"publish_at":"2099-01-01T09:00:00Z"}
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
