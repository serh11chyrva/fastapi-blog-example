# Publication interactions and discussions

All routes below use the `/api/v1` prefix. The backend implements likes and private
saves for posts and published articles, public unquoted post reposts, threaded post
and article replies stored as ordinary posts. Frontend controls are available in publication cards and reading pages.
The Scalar reference at `/api/docs` includes the request/response schemas and examples.

## Visibility and ownership

Only public, unarchived posts and published, unarchived articles participate in interactions. Draft and scheduled
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

`comments_count` includes live entries at every depth of the original post or article
discussion, excluding tombstones and inaccessible archived branches. For a reply publication it counts live direct children. Article `reposts_count` and `reposted` are null.
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

### Automatic author threads

An author thread starts with a standalone post and follows only replies owned by
that post's owner. Multiple author branches are combined chronologically; parent
links retain their exact targets. Replies through another account, article
comments, and self-replies inside somebody else's discussion remain ordinary replies.
`reply.root_id` identifies a root reply, not the original author-thread post.

`GET /posts/{post_id}/thread` returns the original separately and up to 20
continuations by default, with a root-bound ascending cursor and a maximum limit
of 50. Parts use creation time then ID, ascending. Deleted connectors remain only
when needed by a live author continuation; their erased content is never returned.
Owner-visible archives make affected parts read only. The endpoint is private,
no-store, and applies original and branch visibility on every read.

Original cards in public/following feeds, profile timelines, and pins can carry
`thread_preview` with at most two continuations and `has_more`. Continuations and
authors are read in batches. Nested parts contain no further preview or viewer
reaction state. Cached public pages rebuild previews with current branch visibility.
Adding a continuation never changes the original post's creation or feed time.
Membership is derived from existing edges; no migration or thread collection is needed.

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
PATCH accepts post content and attachment changes, but rejects tree metadata. Depth is not capped. Fixed-size parent/root references
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

### Conversation context

`GET /posts/{post_id}/context` returns `{post, original, ancestors}`. For a standalone
post, `original` is null and `ancestors` is empty. Reply context includes a compact
original post/article and only the path to the selected reply, with ancestors ordered
from the oldest reply to its immediate parent. All live authors are loaded in a batch.

Live selected/ancestor posts use the ordinary post response. A deleted reply uses
`{kind: "deleted_reply", id, reply, created_at, updated_at}`; text, author, attachments,
and share slugs are never exposed. Deleted standalone originals remain unavailable.
Archives require the owner of every archived dependency; inherited archive state
makes descendant controls read only. Responses use `Cache-Control: private, no-store`.
Cycles, broken membership, pending posts, and unavailable originals return 404.

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

Profile badges appear beside the public display name, wrapping with long names or
multiple badges. Badge labels, icons, colors, and descriptions remain visible; the
account handle stays on its own line below the name.

- Publication cards and published article pages offer Like, Save, and discussion controls. Posts
  additionally offer Repost. Pressed states and counts come from the original's interaction summary.
  Anonymous readers can read discussions and follow the login link to participate.
- Repost attribution follows the original author's handle. The displayed time is the repost time,
  and hovering shows the exact repost and original publication timestamps, plus the last update when
  it differs from publication. Controls act on the original post. Public and following feeds refresh
  after a repost change. The profile Posts tab merges posts, reposts, and authored article comments,
  with reply/article-comment context after the author's handle and before repost
  attribution and the timestamp. Nested reply labels link to the immediate parent.
  Reply permalinks show the original publication and the complete ancestor path above
  the selected reply. The original article uses a compact card. A visual connector
  joins ancestors; the selected reply has its own emphasized section and direct replies.
  Regular `/posts/{id}` and readable shared URLs use the same conversation view.
  Original-reference cards are not repeated underneath reply content on that page.
- Post timestamps use relative time. Hovering shows the exact publication time and the last update
  when it differs from publication.
- Saved is a protected page at `/saved`, linked from desktop and mobile site navigation. It lists
  saved posts/articles with their ordinary controls; unsaving removes the item from the shelf.
  Explore, Following, profile Posts/Articles, and saved publications load the next page
  automatically within 400px of the list end, including empty cursor pages with older results.
  Only one page is requested at a time; repeated cursors stop automatic loading.
  Errors pause loading and Retry repeats the failed page without clearing loaded entries.
  Deduplication preserves order; offset lists advance by received rows, not visible rows.
  Discussions, follower lists, and article management retain manual pagination.
  Browsers without IntersectionObserver receive a manual fallback button.
- Core reading views use decorative loading skeletons instead of loading paragraphs.
  Feeds, saved publications, and profile publication tabs show three placeholders on
  initial load and two after existing rows during pagination. Search people and
  publications load independently; people start with three rows and append two.
  Profile headers, article previews, post/article reading pages, replies, and follower
  dialogs have matching skeleton layouts. Replies show two placeholders. Shared URLs
  use a neutral reading skeleton until the publication type is known; optional covers
  and attachments are not guessed. Following and Saved also show a neutral skeleton
  during session restoration, without exposing private data.
  Loading messages remain available to assistive technology, and updating result
  regions expose `aria-busy`. Errors remove loading placeholders and retain Retry
  controls and any previously loaded rows. Empty states appear only after a successful
  read. Reaction skeletons occupy only unknown count slots; the controls stay in place.
- Newly mounted publication cards, search results, and replies enter over 180 ms with
  a 4 px offset and a fade, without staggered delays. Article reading content and
  profile headers use opacity only. Ordinary data updates do not remount cards or
  replay their entrances. Shared controls transition colors over 120 ms; pressing a
  reaction or icon button briefly scales its icon without changing layout or confirming
  a mutation before the server response. Publication menus and profile/photo dialogs
  animate only their opening, including dialog backdrops. Closing remains immediate,
  retaining native Escape, focus behavior, and photo-viewer scroll locking. Route
  navigation is immediate and does not wait for page-exit animations. Reduced motion
  removes these effects while retaining the same controls and content.
- Reply/Comments links open the selected publication page at `#replies`, including
  cards in feeds, profiles, search, saved lists, and discussions. Each reply opens
  its own page; replies no longer expand nested branches or inline composers.
  Reading pages keep the discussion open. The selected publication's comment link
  scrolls to its composer; anonymous readers can read replies and sign in to write.
  Article `#comment-<id>` links and comment sorting remain supported.
  Popular reply previews and their per-card requests have been removed.
  Direct reply permalinks scroll to the selected reply; `#replies` scrolls to the
  discussion and focuses its composer for signed-in readers. Deleted reply pages
  preserve navigation to direct children, with no composer for the deleted parent.
  Surviving children retain their own interaction and reply links.

- Shared publication forms enforce the 280-character limit and one attachment choice,
  allow attachment-only replies, disable repeated submission, and keep drafts on failure. Owned live comments offer Edit and Delete; failed edits can reload the
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
  Confirmed external players load automatically near the viewport without media autoplay. Link cards and quoted originals can
  be attached from the composer or the editor.

Request failures remain visible with retry/refresh controls. Viewer changes reset private flags;
requests for previous routes/pages are aborted or ignored on completion. Interaction summaries
stay outside public feed data and use no-store fetches. Frontend controls do not grant access to
private articles or moderation rights; the backend remains authoritative for all mutations.

Reply cards now share post content and interaction controls, including avatars, reposts,
bookmarks, and the comment icon. Profile replies use ordinary feed cards with original
publication context. Short-post previews, including original-post context in replies,
link through their text and image without a separate View post control.
Article and post children load incrementally, retaining tombstones.

The publication composer presents mutually exclusive image, URL, and publication
choices. Images have local thumbnail previews and per-image removal before upload.
Post and reply creation use private staging targets; failed requests keep the local
draft and retry identity. Text is optional when an attachment is ready.

Post and reply editors reuse the same composer. Existing images can be removed
individually, replaced as a gallery, or replaced with another attachment type. Save
commits the final content and queues removed objects for cleanup; Cancel does not
change the saved publication. Edits include the loaded update timestamp to reject
concurrent changes rather than silently overwriting them.

Every publication form shows the current signed-in account's avatar with the normal
initials fallback. Posts, article comments, and nested replies share the same form
layout, attachment controls, progress, and errors. Submit labels are Post for a new
post, Reply for a discussion entry, and Save changes for editing. Reply-target labels
describe the form for assistive technology rather than replacing the submit label.

URL cards use cached metadata with deduplicated reads and at most ten pending refreshes.
Publication responses seed the shared metadata cache before the first render, so
already resolved cards do not briefly show hostname placeholders. Identical URL
requests share one in-flight promise; cache updates reach every mounted occurrence.
Compact link cards retain a bounded left thumbnail and a wrapping text column with
three-line title and description limits. Image loading does not size the row; a
failed image removes its entire column and leaves a usable full-width text card.
Saved metadata remains visible while resolving. The application no longer requires a
Load player button; provider playback controls still require the reader to start media.

Post galleries use a horizontal scroll-snap carousel with up to five images, bounded
arrow navigation, touch scrolling, and a position count. The light image viewer opens
the selected photo, supports arrow keys/Escape, restores focus and page scrolling on
close, and synchronizes the carousel to the last viewed photo.

Publication cards use locally bundled Inter (licensed under the included SIL Open
Font License); article titles retain Georgia. Article covers fade into the white
card over 36px with a concentrated transition near the bottom. Article previews use
the reference's cover, title/date row, excerpt block, and underlined Read article
footer. Excerpts are limited to 66px (three lines at 22px): the first two lines stay
readable and the third fades to fully transparent before the bottom edge, hiding
the summary's continuation. Cover and title/footer links open
the article; the excerpt remains selectable text.
Carousel edges fade over 24px only while more content exists in that direction;
the overlays do not intercept input. Publication date formatting is unchanged.

Single gallery photos use the full post width and their natural height up to 50dvh,
fitting the complete photo without cropping. Multiple
photos share a frame height derived from the first image at 84% of the viewport
width, capped at 50% of the viewport height. Slides use proportional
widths up to the gallery width and contain the complete image without cropping.
Unknown dimensions reserve a 3:2 frame; a failed first photo yields to the first
available photo. Image loading and resizing retain the selected slide.

## Archive visibility and profile pins

Owners can archive their posts, replies, and published articles without deleting
content or relationships. Archived publications, reposts of them, saved cards,
and archived reply branches disappear from public reads and counts. Reference
previews omit them and direct publication/media reads require the archive owner's
session. Featured authors receive no private access. Restoring an original restores
its existing relationships wherever the whole discussion path permits access.

Discussion reads allow an archive owner to inspect its existing conversation,
while independently archived entries belonging to other accounts remain private.
Archived discussions are read only for new interactions. Existing interaction
removal remains idempotent and available for inaccessible originals. Reply authors
can still edit or delete their own accessible content. Deleting a reply preserves
its navigation tombstone and surviving children.

A pin belongs to the original publication and its owner, independently of repost
relationships. Up to five posts, replies, and articles may be pinned in total.
Pins change profile presentation, retain original publication and edit dates,
and do not create feed events or reorder public/following feeds. Archiving or
deleting a publication clears its pin; moving an article out of published state
also clears its pin. Restoring an archive does not restore the pin.

See [Archives and profile pins](API.md#archives-and-profile-pins) for routes,
response timestamps, pagination, visibility, and concurrent limit enforcement.
