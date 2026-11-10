# Application architecture

Backend source lives in `src/backend/`; frontend source lives in `src/frontend/`.
Feature packages own their behavior and persisted models. Shared infrastructure
does not own feature policy.

## Backend responsibilities

Backend classes, functions, and methods use English docstrings. Callable parameters
and return values use reStructuredText fields (`:param name:` and `:return:`).
Ruff uses a target line width of 120 characters, configured in `pyproject.toml`.
Apply backend lint fixes with `uv run --locked ruff check --fix src/backend` and
formatting with `uv run --locked ruff format src/backend`.

- Routers adapt HTTP parameters, cookies, headers, and responses. Endpoint summaries,
  errors, examples, and tags are declared beside each route.
- Application services perform complete mutations with explicit ownership and
  transaction boundaries. They receive `AppResources` and `AuditContext` instead
  of a FastAPI request.
- Repositories contain reusable Beanie queries. Read modules assemble the data
  needed for a response, and presenters map already loaded documents to schemas.
- Beanie documents define persistence fields and indexes. Input/response schemas
  define the API contract; arbitrary external JSON is validated at the boundary.

| Package | Main responsibilities |
| --- | --- |
| `api/` | HTTP endpoints, root and versioned router composition, OpenAPI metadata and examples, Scalar presentation, and the standalone documentation preview |
| `auth/` | Password verification, registration/login, sessions, cookie authentication dependencies, and rate limits |
| `profiles/` | Profile revisions, follows, badge preferences, bounded list reads, and profile presenters |
| `articles/` | Article documents, request/response schemas, validation, repository, service, presenters, share-ID backfill, and scheduled publishing |
| `posts/` | Micro-post documents, request/response schemas, repository, service, presenters, and share-ID backfill |
| `feeds/` | Mixed publication reads, response schemas, presenters, deterministic cursors, and public feed cache invalidation |
| `publications/` | Public share-link resolution, shared readable URLs, typed attachment contracts, image descriptor presentation, and transactional reference validation |
| `interactions/` | Unique likes, private saves, public repost edges, live summary queries, and batched relationship-list hydration |
| `comments/` | Separate post reply trees and flat article comments, bounded reads, batched presenters, and audited mutations |
| `storage/` | Upload preparation, confirmation leases, immutable copies, attachment adapters, object storage access, and cleanup |
| `audit/` | Transport-independent request metadata and transactional audit event writes |
| `core/` | Configuration, typed clients, transaction conflict policy, and application errors |

`main.py` creates the application, registers boundaries, and manages client and
worker lifetimes. `core/security.py` retains compatibility exports for existing
callers; password and token implementation belongs to `auth/security.py`.

`api/router.py` composes the application route tree. Its `api_router` owns the
`/api` prefix and includes `api/v1/router.py`, which owns `/v1` and groups the
authentication, profile, link, article, post, shared-publication, feed, and upload endpoints under
`api/v1/endpoints/`. The outer router also includes `api/endpoints/` for `/`,
`/health`, badge icons, and attached images, preserving their application-root URLs.
Badge assets remain in `profiles/icons/`. Services, repositories, domain models,
and feature schemas remain in their feature packages.

`articles/` and `posts/` each own their document, schema, repository, service, and
presenter layers. Their services enforce ownership, write audit events in the same
transaction as mutations, and queue deleted attachments for cleanup. Neither feature
imports the other feature's code. HTTP adapters live in `api/v1/endpoints/articles.py`
and `api/v1/endpoints/posts.py`, with separate service dependencies.

`feeds/` coordinates both repositories for public, following, and profile publication
lists; feature repositories perform the underlying document queries. `publications/`
resolves shared links through those repositories while preserving post-first lookup
and published-only article visibility. Image URL construction belongs to `storage/`,
and article cover URL construction belongs to `articles/`. Upload orchestration remains
in `storage/`, which imports each feature's models, schemas, and presenters directly.

The original split replaced `content/` without changing HTTP paths, operation names, schema
names, response fields, or MongoDB collection/index names. Typed attachments subsequently extend
the request and response contracts without changing collections or existing image indexes. Existing share IDs remain
valid; each feature owns its legacy share-ID backfill, and the article scheduler is
started from `articles/scheduler.py`.

`api/docs.py`, `api/metadata.py`, and `api/examples.py` own shared API documentation
presentation, response/header/path annotations, and example values respectively.
`api/schemas.py` defines system endpoint responses. Feature schemas reference the
shared examples directly; the `api` package initializer does not import routers.

`api/preview.py` creates a separate documentation application using the main application's
OpenAPI generator without entering its lifespan or registering its runtime routes
or middleware. It creates no infrastructure clients and requires no service settings.
Only Scalar, the OpenAPI schema, and a root redirect are served. A preview notice
is added to a copy of the schema; endpoint contracts and examples remain shared.
`api/docs.py` shares Scalar presentation, with models visible and request testing
and client buttons hidden in the standalone preview.

## Consistency contracts

Session activity changes only activity fields, checks that the session is still
active, and advances `last_seen_at` monotonically. Revocation never depends on
saving a previously read complete session document. Password operations use a
dedicated pool with four worker threads per process.

Session creation saves a validated client type (`web`, `mobile`, or `desktop`) and
an optional native-app device name. Older documents default to `web` without a
migration. Activity refreshes IP and User-Agent without changing the client type
or device name. These raw fields remain internal: `auth/presentation.py` returns
approximate English location labels and parsed browser/device descriptions.
The application owns a GeoLite2 City reader in `AppResources` and closes it at
shutdown. Session presentation runs off the event loop; missing databases and
unresolvable addresses yield `Unknown location` without preventing authentication.

Audited mutations use one MongoDB transaction for the data change and audit event.
Write conflicts become 409 responses. Transaction bodies are not replayed
automatically: callers reload and reconcile before retrying. A dependency failure
can leave the commit outcome uncertain; reload before repeating a write.

Profile edits additionally compare an explicit revision. Avatar attachment advances
that revision once. Public profile schemas exclude email, hidden badge preferences,
and assignment timestamps; own-profile responses explicitly include private settings.

Upload confirmation copies and validates S3 objects before opening the attachment
transaction. A lease serializes confirmation. Attachment changes, the typed saved
result, the audit event, and cleanup changes commit together. Completed confirmations
replay the saved result; avatar HTTP responses load the current own profile after
confirmation. Abandoned copies retain cleanup jobs, and final objects are checked
for attachments before deletion.

## Read contracts

Mixed feeds use post, article, and repost-event response types discriminated by `kind`.
They batch author reads and order by timestamp, publication kind, and ObjectId
descending. Opaque cursors preserve that ordering across collections. Public feed
caching is best effort and expires after 20 seconds; application writes advance its
version when Redis is available.

Own articles and follower/following lists accept offset and limit, returning arrays.
Profile publications also support bounded offset pages. Offset pages can shift
during concurrent changes; refresh from zero when reconciling. See [API.md](API.md)
for exact defaults and limits. Image authorization queries have explicit indexes
on attachment keys.

Article input is validated as a supported TipTap tree before storage. Validation
checks node/mark shapes, parent-child relationships, image sources, and safe links,
with limits on UTF-8 size, depth, node count, and pending traversal work. Image
ownership is checked separately in the article update transaction.

`publications/attachments.py` defines a strict union discriminated by `type`, reused in Beanie
models, request/response schemas, feeds, and TipTap descriptor validation. Missing stored
attachment lists default to empty. Adding a future content kind requires an explicit schema
variant and relevant policy, rather than accepting arbitrary dictionaries. The video variant
is reserved and rejected on all content writes; no video upload or playback is implemented.
`publications/attachment_validation.py` checks account/article references with bounded batched
Beanie queries in the caller's mutation transaction. It checks uploaded image ownership and
rejects reserved video descriptors before persistence. References contain IDs only and never
copy private account or article data; later resolution uses existing visibility rules.

Posts and articles store at most 30 explicit descriptors. Article bodies can independently
contain up to 30 inline mention/hashtag or block attachment descriptors. Article edits validate
references from the resulting body and explicit attachment list together. Ordinary TipTap images
retain their existing validation path. OG metadata is supplied by the caller, and embed metadata
contains an allowlisted provider and HTTPS resource URL; neither triggers an external request.

Image storage inventories remain authoritative for authorization and cleanup. Presenters append
image descriptors for inventory entries missing from explicit placement, so legacy images appear
in the new contract without migration. Posts expose image URLs exclusively in `attachments`;
post and feed schemas have no separate `images` field. Internal `image_keys` remain authoritative
for image authorization and cleanup. Article body descriptors stay in the body. Upload
confirmation removes stale explicit post image descriptors while preserving non-image content.
Top-level clearing removes descriptors, not uploaded objects. API documentation and schema
examples describe these semantics. The frontend reads typed attachments directly and no longer expects a separate post images field.

## Demo fixtures

`backend.seed` is the CLI entry point for the additive fixture loader. `demo/` separates
profile enrichment, publication content, generated PNG media, and social activity.
Stable fixture IDs preserve owner-edited and deleted publications on reruns. A profile audit
event marks one-time location and banner enrichment. The regular discussion service creates
sample likes so reaction edges and counts stay in sync. Private image objects have deterministic
keys. See [the demo tour](DEMO.md) for coverage and repeat-run behavior.

## Frontend responsibilities

- `app/` owns authentication state, a single nested route tree, protected routes,
  and site/reading layouts.
- `features/` owns pages and feature workflows. Session settings live under
  `features/profiles/sessions/`. The article editor separates presentation from
  persistence and upload behavior in `useArticleEditor`.
- `shared/api/` owns transport and explicit frontend contracts. `ApiError` preserves
  HTTP status and error details; TypeScript response types describe the contract
  rather than acting as runtime JSON validation.
- `shared/hooks/` owns reusable bounded list loading. Feed pagination has its own
  cursor hook. Both cancel outdated requests and prevent concurrent load-more calls.
- `shared/ui/` contains common presentation components; `shared/uploads/` implements
  the prepare, direct PUT, and confirm protocol. Its uploader hook retains each pending
  upload ID and the selected File objects while the form remains mounted. A retry after
  PUT success repeats confirmation without uploading or attaching another image. Only
  a definitive expired/missing upload response discards a pending confirmation; an
  uncertain result retains it. Cover completion reloads the article because replayed
  upload responses contain the original saved article snapshot.

Image metadata is validated before post creation. A later upload failure explicitly
reports that the note is already public; retry updates that same note. Avatar and inline
image forms retain failed selections with explicit retry controls. Pending uploads are
kept in memory and are discarded when their form unmounts; after navigation or reload,
inspect current attachments before starting a replacement upload.

Draft and schedule actions make an existing article private before saving content or
cover changes. Local title, cover, and scheduling checks happen before mutations. If
saving or scheduling subsequently fails, the article remains a private draft. Cover
confirmation reloads current article data rather than restoring an old upload snapshot.

Protected routes wait for session restoration. An unavailable authentication service
has an explicit retry state. Route changes cancel outdated reads, and editor form
state is recreated when the article ID changes. A 401 from an authenticated API
operation clears the local session, including when logout finds an expired session.
Login failures remain local to the credential form. Session generations prevent a late
401 from an earlier session from clearing a newly authenticated account.
Loading failures remain distinct
from successfully loaded empty lists.

Cookie security is generated from authentication dependencies. Optional-session
reads explicitly allow anonymous access in OpenAPI. Shared schema generation only
adds examples; it does not infer authentication or response policy from URL text.

Publication documents store `owner_id` independently of the ordered `featured_author_ids` list.
Featured author IDs are unique, exclude the owner, and default to an empty list. A computed `author_ids`
property combines the owner and featured authors for response assembly without persisting a second list.
Only `owner_id` determines editing, upload, private-read rights, scheduler attribution, and owned lists.
Creation sets the caller as owner; featured-author management and collaboration permissions are not implemented.
Owner indexes and featured-author multikey indexes support public profile and following-feed queries.
Shared URLs resolve by the owner's handle. Cursor and author-membership filters are combined with `$and`
to preserve both disjunctions. Presenters receive owner and featured accounts in display order; list
reads load accounts in batches. Responses expose `owner_id` and compact public cards in `authors`.

Profiles store avatar metadata in `avatars.original` as `key` and `content_type`, or null when absent.
An index on `avatars.original.key` supports attachment reads and cleanup. Presenters expose only the
nullable original URL. Resizing, legacy-response adapters, and data/index migrations are not included.
Frontend author cards, ownership checks, and profile images use `authors`, `owner_id`, and `avatars.original` directly.


## Interactions and discussions

`interactions/` stores one `PublicationInteraction` document per publication type, publication ID,
action, and account, protected by a unique index. Like/repost totals are queried from edges;
private save totals are never public. Viewer flags and `/me/saved` use uncached private responses,
so shared feed cache entries contain no account-specific interaction state. State endpoints use
idempotent PUT/DELETE, with audit events only for actual edge changes. Removal remains possible
after the original is deleted or unpublished. Indexes support account lists and repost feed scans.

`publications/access.py` owns the public-original guard reused by discussions and interactions.
During creation or comment mutation it writes `interaction_revision` in the original's transaction,
forcing concurrent deletion/unpublishing to conflict rather than accepting a stale public read.
The revision defaults to zero on legacy documents and is internal; public content timestamps and
feed positions do not change. User interaction changes and their audits commit together. No
transaction body retries are introduced.

`comments/` persists `PostReply` and `ArticleComment` in different collections. Reply positions
store immutable `post_id`, `parent_id`, `root_id`, and integer `depth`; flat comments store only
`article_id` and common content metadata. HTTP bodies forbid extra fields, so article comments
cannot acquire nesting fields. A post parent is checked inside the same transaction and guarded
against concurrent deletion. Replies have no fixed nesting-depth limit; reads fetch only roots
or direct children with ObjectId keyset pagination. Author cards and child counts are batched.
Deletion erases text, hides the author, and retains a tombstone so descendants stay navigable.

Repost edges reference originals rather than copying them. Feed repository aggregation joins
public originals before applying the final page limit; deleted posts cannot surface through a
repost. Feed entries carry either the original's ID/time or the repost edge's ID/time. Cursors
include the event kind, so repeated original IDs do not collapse independently ordered reposts.
Following filters apply to original publication authors or to the reposting account, respectively.
Repost changes invalidate the public feed cache. Profile authored-publication lists stay separate
from public repost history. Saved/repost lists scan bounded relationship pages, hydrate originals
and authors in batches, and return the last scanned ID even when unavailable originals empty a
visible page. Existing collections require no data backfill; Beanie registers the three new
collections and indexes at startup. No new dependency or background worker is required.

See [INTERACTIONS.md](INTERACTIONS.md) for concrete routes, response examples, and access policy.


## Frontend interactions and discussions

`features/interactions/PublicationActions` loads uncached public counts and viewer flags for an
original publication, sends explicit PUT/DELETE desired states, and disables conflicting actions
while requests or reconciliation reads are pending. A local browser event refreshes other mounted
representations of the same original; user-specific flags reset when the account changes. The
private Saved page removes unsaved entries locally and is mounted under a protected route.

Feed cards unwrap repost events while retaining the reposter/time banner and original author
cards, attachments, controls, and ownership checks. Repost changes refresh their containing feed
or profile list. The public profile timeline merges post authorship, repost activity, and live
article comments with the same descending event tuple used by public feeds. Article and shared-post
reading pages reuse these controls and discussions.

`features/comments/Discussion` reads one post level at a time and mounts child lists only when
expanded. Root, parent, and original IDs stay in the API rather than being reconstructed from
visual indentation. Indentation is capped after four levels while deeper replies remain browsable.
Article comments use the flat endpoint, with an @handle shortcut and optional rank sorting.
Unique reaction edges and denormalized counts commit together. Forms retain failed text;
owned live comments support edits/deletes; tombstones preserve expanded child navigation.

`shared/hooks/useCursorList` owns cancellation, first-page/continuation errors, duplicate request
protection, and relationship/comment cursors. Empty visible saved/repost pages do not hide a
remaining cursor. TypeScript unions distinguish original posts, articles, and repost events.
Post reads at `/posts/:postId` provide a fallback when a shared URL is absent. Existing article
editor state retains its current API payload; custom TipTap nodes convert variable attachment
attributes into one editor-local descriptor and back before persistence, preserving strict backend
union shapes. Article images already present in the body are not repeated in the attachment list.
No new frontend runtime dependency is required.
