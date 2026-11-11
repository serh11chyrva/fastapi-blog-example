# Publication interactions and discussions

All routes below use the `/api/v1` prefix. The backend implements likes and private
saves for posts and published articles, public unquoted post reposts, threaded post
replies, and flat article comments. Frontend controls are available in publication cards and reading pages.
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
    "published_at": "2026-10-12T10:03:27Z",
    "updated_at": "2026-10-12T10:06:14Z"
  }
}
```

The outer `id` is the repost edge ID, and outer `published_at` is repost time. The
inner `post` has the original post's ID, publication and update times, owner, and author cards.
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
  "likes_count": 4,
  "liked": true,
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

## Article replies and compatibility routes

`/articles/{article_id}/comments` lists root replies and accepts optional `parent_id`
on reads and creation. Each result includes `parent_id`, `root_id`, `depth`, and
`replies_count`, plus a `publication` containing the ordinary post response for live
entries. Post discussion responses expose the same publication. All text is limited
to 280 characters. Reply metadata cannot be edited.

Existing scoped GET/PATCH/DELETE and like URLs continue to work, resolving migrated
IDs through the stored mapping. Like state is shared with ordinary post interactions;
reply publications can also be saved and reposted. On a reply permalink,
`/posts/{reply_id}/replies` lists its direct children. Original-publication counts
include all live discussion entries; a reply publication count includes live direct children.

Profiles list replies as ordinary posts with immutable discussion context. Their article
card is resolved from the original reference rather than copied. Hidden or deleted
originals hide replies, their images, saved entries, and reposts. Individual reply
deletions preserve tombstones and descendants. See [migration operations](MIGRATIONS.md).

## Frontend flows

- Publication cards and published article pages offer Like, Save, and discussion controls. Posts
  additionally offer Repost. Pressed states and counts come from the original's interaction summary.
  Anonymous readers can read discussions and follow the login link to participate.
- Repost attribution follows the original author's handle. The displayed time is the repost time,
  and hovering shows the exact repost and original publication timestamps, plus the last update when
  it differs from publication. Controls act on the original post. Public and following feeds refresh
  after a repost change. The profile Posts tab merges posts, reposts, and authored article comments,
  with comment activity labeled after the comment author's handle.
- Post timestamps use relative time. Hovering shows the exact publication time and the last update
  when it differs from publication.
- Saved is a protected page at `/saved`, linked from desktop and mobile site navigation. It lists
  saved posts/articles with their ordinary controls; unsaving removes the item from the shelf.
  Saved/repost lists retain Load more even when unavailable originals empty a visible page.
- Reply/Comments opens a discussion within a card; reading pages open the discussion initially.
  A post's View replies button loads only that parent's children. Reply forms appear only for live
  parents. Deleted parents retain their existing branches; deeper live descendants remain usable.
  The article Reply action targets the selected reply. Article pages can
  load a scoped linked comment directly by ID when it falls outside the current page.
- Plain-text forms enforce the 280-character limit, disable repeated submission while pending,
  and keep text on failure. Owned live comments offer Edit and Delete; failed edits can reload the
  latest comment without replacing the local draft. Deletion hides text/author and preserves children.
  Successful creation uses the returned comment immediately in a Just sent section, retaining
  loaded pages and their cursor. The same behavior applies to nested replies. As pagination
  reaches those entries, they move into the ordinary list without duplicate cards.
- Publication ownership and author cards use `owner_id`/`authors`, and avatars use `avatars.original`.
  Post images render only from typed `attachments`. There are no legacy flat-author or image-array
  fallbacks. Post cards omit separate hashtag and account mention labels from attachments.
  Article attachments render outside the body unless the same image already occurs within it.
- Typed TipTap mentions, hashtags, and attachment blocks render and survive editor round trips.
  Account mentions retain their ID label because no public account-by-ID resolver is provided.
  Supported external providers load a player on demand. Link cards and quoted originals can
  be attached from the composer or the editor.

Request failures remain visible with retry/refresh controls. Viewer changes reset private flags;
requests for previous routes/pages are aborted or ignored on completion. Interaction summaries
stay outside public feed data and use no-store fetches. Frontend controls do not grant access to
private articles or moderation rights; the backend remains authoritative for all mutations.

Reply cards now share post content and interaction controls, including avatars, reposts,
bookmarks, and the comment icon. Profile replies use ordinary feed cards with original
publication context. Article and post children load incrementally, retaining tombstones.

The publication composer presents mutually exclusive image, URL, and publication
choices. Images have local thumbnail previews and per-image removal before upload.
Post and reply creation use private staging targets; failed requests keep the local
draft and retry identity. Text is optional when an attachment is ready.

Post and reply editors reuse the same composer. Existing images can be removed
individually, replaced as a gallery, or replaced with another attachment type. Save
commits the final content and queues removed objects for cleanup; Cancel does not
change the saved publication. Edits include the loaded update timestamp to reject
concurrent changes rather than silently overwriting them.
