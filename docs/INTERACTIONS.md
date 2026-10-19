# Publication interactions and discussions

All routes below use the `/api/v1` prefix. The backend implements likes and private
saves for posts and published articles, public unquoted post reposts, threaded post
replies, and flat article comments. Frontend controls and rendering are separate work.
The Scalar reference at `/api/docs` includes the request/response schemas and examples.

## Visibility and ownership

Only undeleted posts and published, undeleted articles participate. Draft and scheduled
articles return 404 from interaction summaries and discussion endpoints, even for their
owner. Returning an article to draft hides its comments and saves from reads; republishing
restores access to existing relationships and comments. Deleted posts hide their reposts
and entire reply trees. No interaction grants private access or authorship credits.

All mutations require an authenticated session and the configured `Origin` header.
An account can change only its own likes, saves, reposts, and comment text. Publication
ownership does not grant moderation or editing rights over other accounts' comments.
Liking, saving, reposting, and commenting on one's own public publication are allowed.

Each mutation commits its data changes and audit event in one MongoDB transaction.
An internal `interaction_revision` write serializes creation and comment mutations
against publication deletion/unpublishing. It does not change the publication's public
`updated_at`, content, authors, or chronological position. Concurrent changes may return
409; reload before retrying. Transaction bodies are never replayed automatically.

## Likes, saves, and repost state

| Method | Path | Access | Result |
| --- | --- | --- | --- |
| PUT / DELETE | `/posts/{post_id}/like` | Session | Add / remove own like |
| PUT / DELETE | `/articles/{article_id}/like` | Session | Add / remove own like |
| PUT / DELETE | `/posts/{post_id}/save` | Session | Add / remove own private save |
| PUT / DELETE | `/articles/{article_id}/save` | Session | Add / remove own private save |
| PUT / DELETE | `/posts/{post_id}/repost` | Session | Add / remove own public repost |
| GET | `/posts/{post_id}/interactions` | Public, optional session | Post counts and viewer flags |
| GET | `/articles/{article_id}/interactions` | Public, optional session | Article counts and viewer flags |
| GET | `/me/saved` | Session | Current account's saved-publication page |
| GET | `/profiles/{username}/reposts` | Public | Account's public repost history |

PUT and DELETE take no request body and return 204. These are desired-state operations,
not toggles: a repeated PUT creates no duplicate edge/event, and a repeated DELETE is
a no-op. A unique index enforces one edge per publication type, publication ID, action,
and account. Repeated PUT retains the original timestamp and list position. Removing
and later adding a save or repost creates a new relationship and position.

Adding an interaction requires a public original. Removing one's own edge is allowed
after deletion or unpublishing, and returns 204 even when no edge exists. Malformed
resource IDs return 404. There are no article repost routes. Saves are never exposed
through other accounts' profiles, public totals, repost feeds, or public relationship lists.

Example post summary:

```json
{
  "likes_count": 12,
  "comments_count": 3,
  "reposts_count": 1,
  "liked": true,
  "saved": false,
  "reposted": false
}
```

`comments_count` includes live entries at every post reply depth, or live flat article
comments, excluding tombstones. Article `reposts_count` and `reposted` are null.
Anonymous `liked` and `saved` are false, as is anonymous post `reposted`. Counts and
viewer flags are read separately and can change concurrently; they are not a single
snapshot. Summaries and private saved-list responses use `Cache-Control: private,
no-store`. Counts and viewer flags are deliberately fetched through these endpoints,
not added to cached public publication/feed representations.

`/me/saved` and profile repost histories accept `limit` (default 20, range 1–50) and
`cursor` (the previous `next_cursor`, at most 24 characters). They scan relationship
ObjectIds in descending order. Invalid ObjectId cursors return 404, while query-size
validation returns 422. IDs are pagination positions, not authorization tokens.

```json
{
  "items": [{
    "id": "68ebd423f2b7a8c901234564",
    "saved_at": "2026-10-14T10:10:00Z",
    "publication": {
      "kind": "micro_post",
      "id": "68eb856f7a02c1349de6b580",
      "owner_id": "68eb731ab54f7c2a9130e6d8",
      "authors": [{
        "id": "68eb731ab54f7c2a9130e6d8", "username": "maya_bennett",
        "display_name": "Maya Bennett", "avatars": {"original": null}
      }],
      "text": "A reading note.",
      "attachments": [],
      "published_at": "2026-10-12T10:03:27Z"
    }
  }],
  "next_cursor": null
}
```

Unavailable originals and originals missing required authors are filtered during
hydration. A page may therefore contain fewer than `limit` visible items or be empty
while `next_cursor` is non-null. Continue until the cursor is null. The continuation
position comes from the last scanned relationship, not the last visible publication.
Edges are retained when originals become unavailable, allowing restoration on article
republishing and explicit cleanup by the account. No new background cleanup is needed.

## Reposts in feeds

A repost stores only the original post reference, reposter, and event time. It accepts
no quotation text. Current original content and author cards are hydrated on reads;
editing the original changes its representation inside reposts. Deleting the original
hides all its reposts. Undoing a repost removes that event from subsequent feed reads.

`/feeds/public` includes all public reposts. `/feeds/following` selects repost events by
followed reposters, so the nested original may be written by an unfollowed account.
Both `kind=all` and `kind=micro_post` include reposts; `kind=article` excludes them.
There is no deduplication between originals and reposts or between different reposters.
An account's own reposts are included in the following feed only when that account
is in the follow filter, following the same rules as original authors.

```json
{
  "id": "68ebd31ff2b7a8c901234560",
  "kind": "repost",
  "reposted_by": {
    "id": "68eb7491d37a2f06b8ce9540", "username": "elliot_gray",
    "display_name": "Elliot Gray", "avatars": {"original": null}
  },
  "published_at": "2026-10-14T10:00:00Z",
  "post": {
    "id": "68eb856f7a02c1349de6b580",
    "kind": "micro_post",
    "owner_id": "68eb731ab54f7c2a9130e6d8",
    "authors": [{
      "id": "68eb731ab54f7c2a9130e6d8", "username": "maya_bennett",
      "display_name": "Maya Bennett", "avatars": {"original": null}
    }],
    "text": "A reading note.",
    "attachments": [],
    "published_at": "2026-10-12T10:03:27Z"
  }
}
```

The outer `id` is the repost edge ID, and outer `published_at` is repost time. The
inner `post` has the original post's ID, publication time, owner, and author cards.
Feed cursors order by event time, event kind, and event ID, so several reposts of one
post paginate independently. Clients must handle the new `kind: "repost"` union
variant and keep passing opaque feed cursors unchanged. Repost mutations invalidate
the public feed cache; personalized flags never enter it. Profile publication lists
remain original authored publications; `/profiles/{username}/reposts` is separate.

## Threaded post replies

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/posts/{post_id}/replies` | Roots, or direct children of query `parent_id` |
| POST | `/posts/{post_id}/replies` | Create a root or child reply |
| GET | `/posts/{post_id}/replies/{comment_id}` | Read a reply or tombstone |
| PATCH | `/posts/{post_id}/replies/{comment_id}` | Replace own live reply text |
| DELETE | `/posts/{post_id}/replies/{comment_id}` | Erase own reply text, preserving descendants |

Root request: `{"text":"A useful observation."}`. Child request:

```json
{"text":"A follow-up thought.","parent_id":"68ebd420f2b7a8c901234561"}
```

`parent_id` is null for roots. A child must reference a live reply in this exact
post. Cross-post, deleted, malformed, and nonexistent parents cannot create a reply.
`root_id` is the root reply ID (a root points to itself), and `depth` is zero for
roots and increments for each generation. These fields and the parent are immutable;
PATCH only accepts `text`. Depth is not capped. Fixed-size parent/root references
avoid storing arbitrarily large recursive documents or ancestry arrays.

```json
{
  "id": "68ebd421f2b7a8c901234562",
  "author": {
    "id": "68eb7491d37a2f06b8ce9540", "username": "elliot_gray",
    "display_name": "Elliot Gray", "avatars": {"original": null}
  },
  "text": "A follow-up thought.",
  "created_at": "2026-10-14T10:05:00Z",
  "updated_at": "2026-10-14T10:05:00Z",
  "deleted": false,
  "post_id": "68eb856f7a02c1349de6b580",
  "parent_id": "68ebd420f2b7a8c901234561",
  "root_id": "68ebd420f2b7a8c901234561",
  "depth": 1,
  "replies_count": 0
}
```

Read roots first, then request `/replies?parent_id=<reply-id>` to load direct
children. There is no recursive full-tree response. Each list returns `{items,
next_cursor}`, ordered by ObjectId ascending, with `limit` default 20 and range 1–50.
Pass `next_cursor` as `cursor` with the same publication and parent filter. The query
continues strictly after that ID; new IDs append naturally. `replies_count` counts
direct children, including tombstones, not all descendants. Missing author accounts
yield a null author card without removing the reply or its descendants.

Deleting a reply sets `deleted=true`, erases stored text, and returns null text and
author on reads. Identifiers, timestamps, root, parent, depth, and child counts stay
available. Descendants are not deleted or moved. A deleted parent can still be read
and traversed, but cannot receive new direct children; live descendants can. Repeated
deletion by the same author returns 204. Deleted text cannot be edited or restored.

## Flat article comments

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/articles/{article_id}/comments` | List or create flat comments |
| GET | `/articles/{article_id}/comments/{comment_id}` | Read a scoped comment |
| PATCH | `/articles/{article_id}/comments/{comment_id}` | Replace own live text |
| DELETE | `/articles/{article_id}/comments/{comment_id}` | Erase own text |

Create and update accept only `{"text":"A useful observation."}`. Unknown body
fields, including `parent_id`, `root_id`, and `depth`, return 422. Article comments
use their own collection and response model with `article_id`; neither contains a
parent, depth, root, or children field. They cannot become threaded through a request.
List responses use the same oldest-first cursor rules and page size as post replies.
Deletion retains a flat tombstone with null text and author. Create returns 201;
updates return 200; deletion returns 204.

Both discussion types accept plain text only, with 1–5,000 characters before trimming
and whitespace-only content rejected. Text is not interpreted as HTML, TipTap, or an
attachment. Non-owned, missing, or cross-publication comment IDs return 404. Comments
are not publications: they have no featured authors, likes, saves, reposts, media
uploads, or feed events in this implementation. Notifications are not sent.
