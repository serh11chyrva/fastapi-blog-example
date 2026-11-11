# FastAPI Blog Example API reference

This guide documents the implemented API in addition to the interactive Scalar reference at `http://localhost:8080/api/docs` and its machine-readable schema at `/api/openapi.json`. Endpoint metadata is declared beside each route; required cookie security is generated from authentication dependencies, and optional-session reads explicitly allow anonymous access.

HTTP handlers live in `src/backend/api/`. The `/api` router includes its `/v1`
child, whose handlers live in `api/v1/endpoints/`. System and image handlers live
in `api/endpoints/` and retain their root paths (`/`, `/health`, and
`/static/images/...`). Shared OpenAPI presentation, annotations, and examples live
in `api/docs.py`, `api/metadata.py`, and `api/examples.py`. This package layout
does not change endpoint URLs, request/response fields, examples, or access rules.

Article and micro-post HTTP adapters are separated into `api/v1/endpoints/articles.py`
and `api/v1/endpoints/posts.py`. Their contracts and business rules belong to the
independent `articles/` and `posts/` packages. Mixed feeds use `feeds/`; shared public
links use `publications/` through `api/v1/endpoints/publications.py`. These module
boundaries preserve the existing operation names, schema names, field descriptions,
and examples used by the generated OpenAPI/Scalar reference at `/api/docs`.

Both the application reference and standalone preview preserve property order from
the OpenAPI schemas, including nested models. Scalar does not alphabetize fields
or move required fields ahead of optional fields, so related fields stay together.
Schema property order follows the Pydantic models, with inherited fields first.
Request and response JSON examples are reordered to match their schemas as well,
including objects inside arrays and publication variants. Example values and array
item order are preserved; keys absent from the schema remain after declared fields.

## Standalone design preview

From the repository root, install dependencies with `uv sync`, then run:

```sh
uv run uvicorn backend.api.preview:app --host 127.0.0.1 --port 8000 --reload
```

Browse <http://localhost:8000/api/docs> or download the schema at
<http://localhost:8000/api/openapi.json>. No Docker, MongoDB, Redis, object storage,
GeoIP database, or environment configuration is required. Scalar browser assets
load from a CDN and require internet access.

The schema includes the full application's current endpoints, fields, security,
errors, and examples, including the upload protocol below. Models are visible and
request testing and client buttons are hidden. This server exposes only the reference,
schema, and `/` redirect; all application endpoints return 404. Uploads, authentication,
image downloads, and health checks cannot be executed. The examples below require
the full application stack; the preview does not provide mock responses.

## Conventions

- Upload size limits are defined in `src/backend/core/config.py`: 5 MiB per avatar, post image, or inline article image, and 10 MiB per article thumbnail. These limits are not configured through environment variables.
- Base path: `/api/v1`.
- Application API requests use JSON. Presigned Garage PUT requests send raw file bytes without application cookies.
- Timestamps are ISO 8601 UTC strings. Account and document IDs are MongoDB ObjectId strings; profile link IDs are UUID strings.
- Authentication is a server-side session delivered in the `session_token` HttpOnly cookie by default; `SESSION_COOKIE_NAME` can override its name. The raw token is never part of a JSON response. The cookie defaults to `SameSite=Lax`; `Secure` is configurable.
- Keep the cookie between application API requests. Use same-origin `fetch` with `credentials: "same-origin"`. All POST, PUT, PATCH, and DELETE requests under `/api/v1` must send an `Origin` matching `APP_ORIGIN` or the optional `APP_ADDITIONAL_ORIGIN` as a CSRF defense. Presigned Garage PUT requests use `credentials: "omit"` and the returned headers. Storage CORS controls browser access to Garage.
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
| GET | `/auth/me` | Session | Get current account and public avatar |
| GET | `/auth/sessions` | Session | List active sessions with client type, location, and device |
| DELETE | `/auth/sessions/{session_id}` | Session | Revoke one of your sessions |
| POST | `/auth/sessions/logout-others` | Session | Revoke every session except current |
| POST | `/auth/logout` | Session | Revoke current session and clear cookie |

Registration request:

```json
{
  "email": "reader@example.com",
  "username": "reader_one",
  "display_name": "Avery Reader",
  "password": "Correct-Horse-Battery-42",
  "client_type": "web"
}
```

The username accepts 3–24 ASCII letters, digits, or underscores; an optional leading `@` is removed before validating the normalized 3–24-character handle, and the value is normalized to lowercase. A 24-character handle may therefore use a 25-character request value when prefixed with `@`. Email is normalized to lowercase. Passwords must contain 12–256 characters. A successful response is `201 Created` and sets the session cookie:

```json
{
  "id": "65f0c2a1b2c3d4e5f6071829",
  "email": "reader@example.com",
  "username": "reader_one",
  "display_name": "Avery Reader",
  "avatars": {"original": null}
}
```

Registration, login, and session lookup return `avatars.original` with the current public avatar URL or null.
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

Both registration and login accept `client_type`: `web` (default), `mobile`, or `desktop`. It is saved at creation and cannot change during the session. Mobile and desktop apps can also send `device_name`, a printable, nonblank label of at most 128 characters (surrounding whitespace is trimmed). Web sessions ignore this label and derive the browser and OS from User-Agent. These client-supplied labels are display metadata, not proof of device identity or an authorization mechanism. Existing sessions without a client type are treated as `web`.

Example mobile login:

```json
{"identifier":"reader@example.com","password":"Correct-Horse-Battery-42","client_type":"mobile","device_name":"iPhone 16"}
```

All client types currently use the same cookie-based authentication and must supply the configured `Origin` on mutations, including registration and login. Native apps must retain and send the session cookie.

Session list response:

```json
[
  {
    "id": "65f0c2a1b2c3d4e5f6071830",
    "created_at": "2026-10-12T09:30:00Z",
    "last_seen_at": "2026-10-12T09:34:15Z",
    "expires_at": "2026-11-11T09:30:00Z",
    "client_type": "web",
    "location": "Kyiv, Ukraine",
    "device": "Chrome 141.0.0 on Windows 10",
    "current": true
  }
]
```

`location` is an approximate English `city, region, country` label from the latest recorded IP, omitting missing and duplicate parts. It is computed locally with GeoLite2 City. Private, invalid, and unknown IPs, missing records, or an unavailable database produce `Unknown location`; no raw IP fallback is returned. `device` uses the latest recorded User-Agent: browser and OS for web, or the saved device name and parsed OS for mobile/desktop (falling back to parsed device/OS). Unrecognized User-Agents yield `Unknown browser` or `Unknown device`. Raw `ip_address` and `user_agent` are retained internally for session activity and auditing but are no longer fields in this response.

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
| GET | `/users/{username}/timeline` | Public | Page through authored posts, reposts, and authored article comments |
| POST | `/me/avatar/uploads` | Session | Prepare an avatar upload |
| POST | `/me/avatar/uploads/{upload_id}/complete` | Session | Confirm and replace avatar; return current own profile |
| POST | `/me/banner/uploads` | Session | Prepare a profile banner |
| POST | `/me/banner/uploads/{upload_id}/complete` | Session | Confirm and replace the profile banner |
| DELETE | `/me/banner` | Session | Remove the current profile banner |
| GET | `/users/{username}/followers` | Public | List followers |
| GET | `/users/{username}/following` | Public | List followed accounts |
| PUT | `/users/{username}/follow` | Session | Follow account (idempotent) |
| DELETE | `/users/{username}/follow` | Session | Unfollow account (idempotent) |

Article comment events in the profile timeline include the comment's `created_at` and `updated_at`.

### Profile edits and concurrency

Read `GET /me/profile` before editing and send its `revision` with every profile or badge visibility PATCH. Revision is an optimistic concurrency counter, independent of data format `version`. Every successful PATCH increments it, including no-op updates. Attaching an avatar or banner or removing a current banner also increments it once. Stale revisions or concurrent transactional writes return `409` with `{"detail":"Profile changed; reload your profile before saving"}`. Reload and explicitly reconcile edits before retrying; do not automatically resubmit an old form with a new revision. Missing revision returns `422`, including for older clients.

Editable fields are partial: omitted or null values stay unchanged. `display_name` is trimmed, nonblank, and limited to 64 characters, `bio` to 280, `location` to 80, and `links` to eight entries. An empty location clears it. Labels are trimmed and allow 1–32 characters; URLs allow 8–500 characters and require absolute HTTP(S) URLs with a hostname, without credentials, whitespace, control characters, or backslashes. The same link validation applies to persistence models. Use `[]` to clear links. Unknown top-level profile fields return `422`.

```json
{
  "revision": 0,
  "display_name": "Avery R.",
  "bio": "Writing about books and software.",
  "location": "Kyiv, Ukraine",
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
  "location": "Kyiv, Ukraine",
  "links": [{"version":1,"id":"da3861fe-4336-411f-8e34-e32d37c2ebad","label":"Website","url":"https://example.com","platform":"website","redirect_url":"/api/v1/links/da3861fe-4336-411f-8e34-e32d37c2ebad/redirect"}],
  "avatars": {"original": "/static/images/avatars/0123456789abcdef0123456789abcdef.png"},
  "badges": [{"version":2,"code":"early-reader","payload":{"label":"Early Reader","description":"Joined the demo community early.","background_color":"#f3f4f6","text_color":"#374151","icon_url":"/static/images/badges/star.svg","icon_color":"#374151"}}],
  "joined_at": "2026-10-12T08:42:19Z",
  "posts_count": 12,
  "banner_url": null,
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

### Public profile activity

The timeline returns `{items, next_cursor}` in descending event time, kind, and ID order.
The default limit is 20 and the maximum is 50. Continue with the opaque cursor
from the preceding page. An unknown profile returns 404. Each item is a `micro_post` or `repost`. Replies are ordinary micro-posts with immutable
`reply` context. The client resolves that context into a badge and original-publication
card. Deleted entries and replies to unavailable originals are omitted.
The public profile's `posts_count` counts visible posts crediting the user as an author.

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
| POST | `/me/banner/uploads` | Prepare one banner up to 5 MiB |
| POST | `/me/banner/uploads/{upload_id}/complete` | Replace the banner and return the current own profile |
| DELETE | `/me/banner` | Detach the current banner and queue cleanup |
| POST | `/posts/{post_id}/images/uploads` | Prepare one to five gallery images, in display order |
| POST | `/posts/{post_id}/images/uploads/{upload_id}/complete` | Replace the whole gallery; returns post |
| POST | `/articles/{article_id}/cover/uploads` | Prepare one cover |
| POST | `/articles/{article_id}/cover/uploads/{upload_id}/complete` | Replace cover; returns article with `thumbnail_url` |
| DELETE | `/articles/{article_id}/cover` | Detach the cover and queue cleanup |
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

The server validates a separate final copy and attaches it in a transaction with the audit event. Replaying the temporary PUT cannot overwrite that final image. Repeating a completed confirmation does not attach again. Publication confirmations return the original saved result; avatar and banner confirmations return the current own profile and revision, including when replaying a completed upload from an older API format. A failed gallery confirmation leaves existing attachments intact. Concurrent edits can return `409`; retry confirmation while the upload is valid. If it expires, prepare a new upload.

Preparation and PUT URLs last ten minutes. Completion must start before the deadline and has a five-minute processing lease. Missing files, expired sessions, and concurrent confirmations return `409`; missing or inaccessible upload sessions return `404`. Oversized images return `413`, unsupported bytes return `415`, and size mismatch or count limits return `422`. Storage/database failures return `503`. Temporary files and abandoned final copies are queued for cleanup after an hour; replaced and deleted attachments are queued immediately. The worker runs every minute and retries failed deletions. Upload-session results are retained for seven days after expiry.

Downloads are at the application root, outside `/api/v1`:

| Method | Path | Access |
| --- | --- | --- |
| GET | `/static/images/avatars/{object_name}` | Public, attached avatar |
| GET | `/static/images/post-images/{object_name}` | Public, non-deleted post |
| GET | `/static/images/profile-banners/{object_name}` | Public while attached |
| GET | `/static/images/article-covers/{object_name}` | Published article or its owner |
| GET | `/static/images/article-images/{object_name}` | Published article or its author |

Only attached images are served. Missing, deleted, or inaccessible images return `404`; unavailable storage returns `503`. Article images use `Cache-Control: private, no-store`, including published articles, so returning an article to draft does not leave a publicly cached copy. Avatars and post images use a one-hour public cache. TipTap image sources must use the new relative article-image paths and belong to the article being saved. Legacy multipart upload routes and `/api/v1/media/` download routes are removed, without migration or redirects.

Following yourself returns `400`. Repeated follow/unfollow requests are safe and return `204`.

## Publication authors and avatar variants

Micro-posts, full articles, all feed items, profile publication lists, and shared-publication responses
return `authors`, a nonempty array of public profile cards in display order. Each card contains only
`id`, `username`, `display_name`, and `avatars`. Responses also expose `owner_id` separately.
The array contains the owner first, followed by `featured_author_ids` in stored order. Featured authors
are display credits and receive no editing, upload, or private-read rights; those depend only on `owner_id`.
Creation sets the caller as owner and leaves featured authors empty. Adding/removing featured authors
and collaboration permissions are not implemented. Public profile lists and following feeds match the
owner or a featured author; `/me/articles` lists only owned articles. Shared URLs use the owner's handle.

Public profiles, own profiles (including avatar confirmation), follower/following cards, and publication
authors return `avatars: {"original": "/static/images/avatars/..."}`. The `avatars` object is always
present; `original` is null when no avatar is set. Only the original variant is currently available;
automatic resizing is not implemented. Clients should allow additional variant keys in future responses.

This replaces the previous flat publication author fields and profile avatar URL field. Clients must
read `authors` and `avatars.original`; the old response fields are no longer emitted. Request payloads
are unchanged. Publication documents require `owner_id` and store an ordered `featured_author_ids`
list (empty by default). Featured IDs must be unique and cannot contain the owner. The combined
`author_ids` list is an internal computed property, not a stored field. Profiles store image metadata
under `avatars.original` (`key` and `content_type`), or null when absent. No migrations or
legacy-response adapters are included; existing data, saved upload results, and indexes require a
separate migration before use with this schema.

## Feeds

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/feeds/public?kind=all&limit=20` | Public | Chronological mixed feed |
| GET | `/feeds/following?kind=all&limit=20` | Session | Chronological feed from followed accounts |

Feed items are a discriminated union: `micro_post` requires text, `article` requires title and summary, and `repost` wraps an original `post` with `reposted_by`, its own event ID, and repost `published_at`. Original-publication variants retain unused alternative fields as null. `kind=all` and `kind=micro_post` include post reposts; `kind=article` excludes them. In following feeds, reposts are selected by followed reposters rather than the original post author. Originals and repost events are not deduplicated. See [reposts in feeds](INTERACTIONS.md#reposts-in-feeds) for the new event shape.

Original feed publications carry `published_at` and `updated_at`. A cached response from an older version can have a null `updated_at`.

`kind` is `all`, `micro_post`, or `article`. `limit` is 1–50 (default 20). When `next_cursor` is non-null, pass it unchanged as the next `cursor` query parameter. Do not construct or edit cursors.

```json
{
  "items": [
    {
      "id": "65f0c2a1b2c3d4e5f6071831",
      "kind": "micro_post",
      "title": null,
      "text": "A small idea worth sharing.",
      "attachments": [],
      "summary": null,
      "owner_id": "65f0c2a1b2c3d4e5f6071829",
      "authors": [{"id":"65f0c2a1b2c3d4e5f6071829","username":"reader_one","display_name":"Avery R.","avatars":{"original":null}}],
      "published_at": "2026-10-12T09:34:15Z"
    },
    {
      "id": "65f0c2a1b2c3d4e5f6071832",
      "kind": "article",
      "title": "Notes on reading",
      "text": null,
      "summary": "A few practical ideas.",
      "owner_id": "65f0c2a1b2c3d4e5f6071829",
      "authors": [{"id":"65f0c2a1b2c3d4e5f6071829","username":"reader_one","display_name":"Avery R.","avatars":{"original":null}}],
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
| PATCH | `/posts/{post_id}` | Owner | Replace post text and optional typed attachments |
| DELETE | `/posts/{post_id}` | Owner | Soft-delete post |
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
  "attachments": [],
  "owner_id":"65f0c2a1b2c3d4e5f6071829",
  "authors": [{"id":"65f0c2a1b2c3d4e5f6071829","username":"reader_one","display_name":"Avery R.","avatars":{"original":null}}],
  "created_at":"2026-10-12T09:34:15Z",
  "updated_at":"2026-10-12T09:34:15Z"
}
```

Text is trimmed and limited to 280 characters. Empty text requires an attachment in the final saved state. `PATCH` may omit `text` to preserve it; an omitted `attachments` field preserves existing descriptors, while `[]` clears them and `null` returns 422. Creation defaults to no explicit descriptors. A missing, deleted, or non-owned post returns `404` for edit/delete.

## Articles

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/articles` | Session | Create a draft |
| GET | `/me/articles?status=all` | Session | List own articles |
| GET | `/articles/{article_id}` | Public / owner for draft | Read article |
| PATCH | `/articles/{article_id}` | Owner | Partially update article |
| POST | `/articles/{article_id}/publish` | Owner | Publish draft |
| POST | `/articles/{article_id}/schedule` | Owner | Schedule a future publication |
| POST | `/articles/{article_id}/draft` | Owner | Return an article to draft |
| DELETE | `/articles/{article_id}` | Owner | Soft-delete article |

Create an article as a draft, then edit or publish it. `status` for the author list is `all`, `draft`, `scheduled`, or `published`. The author list accepts `offset` (default 0) and `limit` (default 20, maximum 100), ordered by updated time and ID descending. Request the next offset until fewer than limit entries are returned; there is no silent 100-article cutoff. Profile publication lists accept offset and limit too (default/maximum 50). Offset pagination can shift when publications are added or edited; refresh from offset 0 when reconciling changes. A draft request body uses TipTap JSON, not HTML. Supported nodes/marks are document, paragraph, heading levels 1–3, text, hard break, horizontal rule, bullet/ordered list, list item, blockquote, code block, bold, italic, strike, code, and HTTP(S) links. The JSON document is limited to 1,000,000 UTF-8 encoded bytes, 64 nesting levels, and 10,000 content nodes. The node budget is checked before enqueueing child nodes, so a wide tree is rejected without expanding an unbounded traversal queue. Every node, attribute object, mark list, and child array is validated. Null child/mark arrays, unsupported nodes, and invalid parent-child structures return 422. Documents and blockquotes require block content; lists require list items; list items start with a paragraph.

Upload an optional cover through `/articles/{article_id}/cover/uploads` and its matching confirmation endpoint (JPEG, PNG, or WebP; 10 MiB maximum). A published thumbnail is public; while an article is a draft or scheduled, only its author can retrieve the image. Set a future ISO 8601 timestamp with timezone to schedule publication (replace the illustrative date with your intended future time):

```json
{"publish_at":"2099-01-01T09:00:00Z"}
```

The scheduler checks every 15 seconds. Returning to draft clears a pending schedule or unpublishes an article. Deleting an article soft-deletes it and removes it from public feeds.

```json
{
  "title": "Notes on building a reading habit",
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

Article summaries are read-only, generated on save from the first 280 characters of normalized body text.

Article response adds `id`, `kind: "article"`, `status`, `owner_id`, `authors`, `created_at`, `updated_at`, and nullable `published_at`. `PATCH` accepts any subset of `title`, `body`, and `attachments`. Omitted or null article fields preserve their current values; `attachments: []` clears explicit descriptors. Published articles are publicly readable. Draft reads by anyone except the owner return `404`.

## Typed publication content

Posts and articles store an ordered `attachments` array. Each object is a strict discriminated
union selected by `type`; unknown types and fields return 422. Articles allow up to 30
explicit descriptors. Posts and replies allow one gallery of up to five images or
one player, card, link, or publication reference. Mention and hashtag descriptors
are article-only. Empty post text is allowed with a valid attachment.
The composer and editor support link cards, publication references, and embedded provider players. The editor preserves supported TipTap nodes during save and reload.

| Type | Fields | Behavior |
| --- | --- | --- |
| `image` | `url`, optional `alt` (up to 1,000 characters, default empty) | Same-origin URL of an image uploaded to this exact post or article |
| `link` | `url`, optional `label` (1–200 characters) | Plain HTTP(S) link |
| `mention` | `user_id` | 24-character ObjectId of an existing account; no notification is sent |
| `hashtag` | `tag` | 1–64 Unicode letters, digits, or underscores, without `#`; case is preserved |
| `og_card` | `url`, `title` (1–300), optional `description` (up to 1,000, default empty), `image_url`, `site_name` (1–200) | Caller-supplied or server-generated preview metadata |
| `article` | `article_id` | 24-character ObjectId of an existing published, undeleted article |
| `post` | `post_id` | 24-character ObjectId of an existing public micro-post |
| `embed` | `provider`, `url` | HTTPS resource descriptor for `soundcloud`, `spotify`, `youtube`, or `vimeo`; legacy `twitch` descriptors remain readable as cards |
| `video` | `url` | Reserved schema variant; all writes currently return 422, including TipTap nodes |

External URLs are limited to 2,048 characters and require HTTP(S), a hostname, no credentials,
and no whitespace, control characters, or backslashes. Embed URLs additionally require HTTPS,
the standard port, and a concrete supported resource path. A background worker confirms
YouTube, Vimeo, Spotify, and SoundCloud resources before returning a player URL.
Players load near the viewport without an extra activation button; media does not
autoplay. Homepages, unavailable resources, and unsupported providers use cards.

```json
{
  "text": "Notes for the reading group.",
  "attachments": [
    {"type":"og_card","url":"https://example.com/notes","title":"Reading notes","description":"Ideas to revisit"}
  ]
}
```

Use existing public publication IDs when attaching a post or article. Reference checks occur
inside the publication mutation transaction; invalid or unavailable references return 422.
An attachment stores the ID of the account or publication. For cards, pass up to 30 repeated
`ref=article:<id>` or `ref=micro_post:<id>` values to `GET /publications/previews`.
The response is an array of compact cards in request order. Micro-post cards include the original
post's `updated_at`. The response omits unavailable originals and nested references.
Retaining an existing reference in an edit is allowed
after its target becomes unavailable. Attachments grant no ownership, private access, featured
credit, notifications, or automatic hashtag discovery.

Images still use the existing prepare/PUT/confirm upload protocol, with five images per post
and 30 inline images per article. Reserve a private post with `/posts/drafts`, upload
images, then PATCH its complete content to publish. Articles upload into an owned
draft. Optional `image` descriptors provide alternate text or gallery ordering.
Repeating an image URL within explicit/body descriptors is rejected. Upload inventories
(`image_keys` / `inline_image_keys` in storage) and their cleanup/authorization indexes remain authoritative.
Post responses expose images only as `type: "image"` entries in `attachments`; the separate `images`
field is removed, including in feeds, profile publications, shared-post reads, and upload confirmation
responses. Article responses retain their separate `inline_image_urls` upload inventory.
Clearing explicit descriptors alone does not delete uploaded files. Send
`retain_image_urls` to remove post images, or transfer a private `image_draft_id`
to replace a gallery atomically. Direct upload confirmation rejects mixed gallery
and non-image attachments; use staging to change attachment types.

Post, article, shared-publication, feed, and profile-publication responses expose `attachments`.
They retain explicit descriptor order, then append typed descriptors for uploaded images without
explicit placement (including legacy images). Article responses can consequently
exceed 30 descriptors: their limit applies to explicit stored descriptors. Posts
and replies remain limited to one attachment choice. Article body descriptors remain in the body and
are not copied into the top-level list. Article covers remain a separate `thumbnail_url`.

### External link preview

Send `{"url":"https://example.com/"}` to `POST /links/preview` with a session and Origin.
The result is a cached, ready-to-store `og_card`, or a hostname card while background
resolution is queued. The worker fetches public HTTP(S) hosts on standard ports,
with up to three redirects, five seconds per request, and 512 KiB per response. The endpoint
accepts up to 20 requests per minute per account and IP. A blocked destination returns 422,
rate limiting returns 429, and unavailable metadata falls back to the original hostname.
The fetch never proxies page bodies or stores external image copies. Declared Open Graph
image groups are tried in order (secure variant before the group's URL), followed by
Twitter images. Relative image URLs use the final redirected page URL. The worker
probes at most 12 candidates with a 1 KiB range read, three seconds per probe, and
an eight-second total image budget. Every redirect uses the public-address checks;
unreachable candidates are skipped and no usable image yields a text-only card.

### TipTap references and embedded content

Text may carry an `underline` mark. Paragraphs and headings accept `attrs.textAlign`
(`left`, `center`, `right`, or `justify`). Blockquotes accept `attrs.citation` up to 200
characters. Code blocks accept a language identifier such as `javascript`.

In addition to existing nodes and marks, paragraphs and headings support inline `mention`
and `hashtag` leaf nodes. Their `attrs` contain `user_id` or `tag` respectively, without `type`.
Block positions support an `attachment` leaf whose `attrs` contain a complete typed descriptor.
These nodes cannot contain child content, text, or marks. A body supports up to 30 such descriptors
independently of the top-level attachment limit and retains its existing byte, depth, and node limits.

```json
{
  "type": "doc",
  "content": [
    {"type":"paragraph","content":[
      {"type":"text","text":"Discussed with "},
      {"type":"mention","attrs":{"user_id":"68eb7491d37a2f06b8ce9540"}},
      {"type":"text","text":" "},
      {"type":"hashtag","attrs":{"tag":"reading"}}
    ]},
    {"type":"attachment","attrs":{
      "type":"embed","provider":"spotify",
      "url":"https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
    }}
  ]
}
```

Article creation validates descriptors without any preuploaded images. On body or attachment
edits, references in the resulting body and top-level list are validated together; ordinary image
nodes continue to require images uploaded to the containing article. Reference availability is
checked on content writes, not continuously or during scheduled publication. Only IDs remain
when referenced resources later disappear. The OpenAPI union, rich request/response examples,
and these rules are exposed in the Scalar reference at `/api/docs`.

## Likes, saves, reposts, and discussions

The backend now provides likes and private saves for public posts and published articles,
public unquoted post reposts in feeds, and publication-backed post and article reply trees.
See [the interaction and discussion reference](INTERACTIONS.md) for endpoint tables,
request/response examples, cursor rules, privacy, ownership, tombstones, and concurrency guarantees.
Scalar at `/api/docs` includes the new Interactions and Comments endpoint groups.

- PUT/DELETE `/posts/{post_id}/like`, `/save`, and `/repost` set the current account's state.
- PUT/DELETE `/articles/{article_id}/like` and `/save` set article state; articles cannot be reposted.
- GET the matching `/interactions` endpoint for public counts and optional private viewer flags.
- GET `/me/saved` for only your saved publications; GET `/profiles/{username}/reposts` for public reposts.
- `/posts/{post_id}/replies` supports roots and direct children via `parent_id`.
- `/articles/{article_id}/comments` supports `sort=newest` or `sort=most_liked` and rejects parent fields in create/update bodies.
- PUT/DELETE a scoped comment or reply's `/like` endpoint to set a reaction on a live entry.

All mutations require a session and Origin. Only public originals can receive interactions or
comments; interaction removal also works after the original becomes unavailable. Comment authors
can edit/delete only their own content. Deleted comments retain null-text, null-author tombstones
and preserve descendants. Viewer state and saved lists are never publicly cached. Existing
publication response shapes stay unchanged; feeds add a `kind: "repost"` variant.

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

### Unified reply publications

Replies are posts with immutable `reply` metadata (`kind`, `publication_id`, `parent_id`,
`root_id`, `depth`). Text is limited to 280 characters. Scoped discussion routes remain
available and include the live post in `publication`; ordinary post URLs and interaction
routes also apply. Article replies support child threads. Feed cursors issued before
this migration are invalid; restart pagination. See [migration operations](MIGRATIONS.md).

### Private post upload targets

`POST /posts/drafts` accepts `{ "key": "a-client-generated-UUID" }`. Reuse the key
on retries; the response identifies an owner-only staging post. Existing image upload
routes accept this target. PATCH the final content to publish it, or DELETE it to
abandon it. Inactive unpublished targets expire after 24 hours. They are excluded
from feeds, profiles, previews, shared links, interactions, and public image reads.

### Short-publication content rules

Posts and replies accept empty text only when the saved state contains an attachment.
Choose one gallery (one to five images), one player, one link card, or one publication
reference. This limit does not apply to article body blocks. On PATCH, omitted text and
attachments are preserved. `retain_image_urls: []` removes the entire gallery; a list
retains and orders only the owned images listed. `image_draft_id` transfers a completed
private gallery atomically on save. `expected_updated_at` returns 409 on a stale edit.
Removing the final attachment from a textless post is rejected.

`POST /links/resolve` returns `status`, a fallback `card`, the resolved `attachment`,
and an optional server-constructed `player_url`. Provider homepages and unsupported
resources become cards. Provider metadata is confirmation at resolution time, not a
guarantee of future playback. Arbitrary iframe markup is never stored or rendered.

Upload draft responses include `pending: true` and a null `share_url`; public posts
and replies have `pending: false`. Reusing a draft key returns the same committed
publication after a lost response. Clients must not upload into that published
result when retrying creation. Reusing a reply draft is scoped to its original
publication and immediate parent. `retain_image_urls` applies when finalizing a
reply or transferring an image draft as well as when editing a post; omitted URLs
are queued for cleanup after the transaction. Edit timestamps compare at MongoDB's
millisecond precision. New quoted posts must be public, including their original
discussion; private staging posts cannot be quoted.
