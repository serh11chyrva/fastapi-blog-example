# Publication and editor improvements

Status: all 15 implementation steps and follow-up integration fixes are committed.
Automated and manual application checks require a separate user request.
Operational migration progress is recorded below.

## Scope and reference material

Implement the nine requested publication, reply, attachment, link-preview, editor, and gallery improvements as sequential Conventional Commits. Each implementation commit includes its relevant documentation and API description/example changes.

Design references supplied by the user:

- `01-pulse-rich-content-v19.html`: horizontal photo carousel and lightweight image viewer.
- `07-pulse-longread-editor.html`: block insertion, selection formatting, contextual controls, drag-and-drop, and rich content editing.

The HTML files are behavior and appearance references, not repository instructions. Adapt their behavior to the existing React/TipTap implementation; do not import their bundled application, demo assets, or persistence assumptions.

## Working decisions

- Remove author-entered article summaries from the editor and write API. Retain a read-only, persisted `summary` for previews, derived on every body save from the first 280 characters of normalized body text. Traverse text nodes in reading order, separate blocks with whitespace, ignore markup and non-text attachment metadata, and do not add an ellipsis beyond the limit. An article with no textual body has an empty summary. Backfill existing articles.
- A reply is a `MicroPost` with immutable discussion metadata, not a third publication entity or a copied post. Articles remain their own long-form entity. Discussion metadata identifies the original article/post, immediate parent reply, root reply, and depth. Existing article comments become root replies; subsequent replies can use the same tree behavior as post discussions.
- Posts and replies share a 280-character limit. The user authorized truncating synthetic legacy replies to 280 characters during migration.
- Treat one gallery of one to five images as one attachment choice. Other choices are one verified player, one link card, or one publication reference. Preserve the existing ability to reference a post as well as an article. The one-choice rule applies to short posts/replies, not to the block contents of long-form articles.
- Derive the article context card and reply badge from immutable discussion metadata. This is a system-provided context reference, not a second author-selected attachment; do not store a second copy of the article. Resolve it with current visibility rules.
- Keep current discussion visibility rules: an unavailable original hides its discussion from public reads, including profile entries, direct reply URLs, and reposts. Deleting an individual reply retains a tombstone for navigating descendants.
- Replies appear as ordinary publication cards on their authors' profiles. Preserve the current main-feed scope initially: top-level posts and explicit reposts; do not flood it with all replies merely because they share a collection.
- A player loads automatically when its card enters view, without an extra application-level activation button. This does not mean media autoplay. Cached metadata and actual provider playback are separate concerns.

## Baseline findings before implementation

- `comments/models.py` stores `PostReply`, `ArticleComment`, and `CommentLike` separately from `posts/models.py::MicroPost` and `PublicationInteraction`.
- `profiles/timeline.py` merges article comments as a separate event type. Sharing, cursors, saved lists, and interactions therefore need coordinated migration.
- `PostComposer.tsx` requires text, creates a public post, and only then uploads its images. `FeedCard.tsx` only edits text. Clearing attachment descriptors alone cannot remove images because `image_keys` is also used to construct responses.
- `PublicationAttachments` currently allows 30 descriptors and is shared with articles. The short-post constraint must not accidentally restrict article bodies.
- `links/preview.py` already provides bounded public-URL fetching, redirect checks, DNS/address protection, and text metadata fallback. It has no metadata cache or background queue and does not extract preview images.
- Backend embed validation primarily checks provider hostnames; frontend `embedSource.ts` already checks several resource paths. A bare SoundCloud homepage is rejected by that frontend helper today, but server validation and actual embeddability still need to agree.
- `Attachments.tsx` currently gates iframe creation behind a button. `MediaGallery.tsx` renders a grid and a looping viewer, while the reference uses a horizontal carousel and bounded navigation.
- The article editor already uses TipTap. Its toolbar follows the current selection and inserts after the active block; the reference also provides insertion gaps, slash commands, selection preservation, keyboard block movement, and an explicit drop indicator.

## Sequential commits

### 01 — `feat(articles): derive summaries from article content`

- Add a backend text extraction helper and recompute `summary` when saving a body, including drafts and scheduled articles.
- Remove `summary` from create/update payloads and the publishing form; keep it read-only in response/preview types.
- Add an explicit, resumable backfill for existing articles and invalidate affected preview/feed caches.
- Update article schemas, endpoint examples, `docs/API.md`, and editor documentation.

Completion criteria: all article previews use at most 280 characters derived from saved body text; no manual summary field remains in the UI or write contract.

### 02 — `refactor(posts): add publication-backed reply metadata`

- Extend `MicroPost` with optional immutable discussion metadata and indexes for direct children, root threads, ranking, and profile pages.
- Add focused shared helpers for original/parent access, ownership, soft deletion, and reply counts.
- Keep existing storage routes working during this additive step. Update all generic post queries so newly introduced reply records cannot leak into unrelated feeds.
- Define response shapes and the distinct ordinary-post/reply text limits without changing article-body constraints.

Completion criteria: the unified model can represent every existing reply tree and flat article comment, including tombstones, without losing information.

### 03 — `feat(migrations): migrate discussions into publication posts`

- Add a versioned, explicit migration command with batches, a checkpoint, a single-run lock, and an optional read-only report mode. Do not perform the large conversion on each API startup.
- Map legacy source collection and ID to a unique post ID. Preserve IDs when possible; use a persisted mapping for collisions. Keep ownership, timestamps, text truncated to 280 characters, tree relationships, and deleted state.
- Convert article comments into article-rooted replies and `CommentLike` records into unique publication likes. Do not invent unavailable historical reaction timestamps; document a deterministic fallback.
- Preserve old discussion URLs through the mapping and route adapters. Keep historical audit records interpretable.
- Rebuild derived counts, add indexes, and version or invalidate incompatible feed/profile cursors and caches at cutover.
- Write an operational runbook covering backup, write pause, migration, optional reconciliation, resumption, and rollback. Retain legacy collections; do not delete them in this series.

Completion criteria: rerunning or resuming conversion cannot duplicate posts, likes, or mappings; descendants and existing links remain addressable. Conversion and application cutover are deployed together, not between live legacy writes.

### 04 — `refactor(discussions): use posts for replies and reactions`

- Switch discussion creation, editing, deletion, listing, and ranking to publication-backed replies. Preserve transaction guards against concurrent parent/original deletion.
- Route likes, saves, and reposts through existing publication interactions. Preserve descendant navigation when a reply is deleted.
- Update profile timelines, publication previews, direct/shared URLs, repost hydration, saved lists, and counters to use one identity per reply.
- Keep legacy endpoints as compatibility adapters to the new storage, with no ongoing duplicate writes. Distinguish total discussion counts from a reply's own child/descendant counts in the API.
- Hide unavailable originals consistently across every read path, including profile/repost paths.

Completion criteria: a reply is editable, shareable, and repostable as the same post everywhere, with consistent counts and access rules.

### 05 — `feat(replies): render replies with shared post controls`

- Reuse focused author, body, attachment, and action components from publication cards in `Discussion`, `HighlightedReplies`, and profile activity.
- Add avatars and repost controls to replies. Replace the visible `Open discussion` text with the comment icon, retaining an accessible label and tooltip.
- Render article replies on profiles with their reply badge and current article preview. Open the correct reply/thread from links and comment actions.
- Update shared API types and remove frontend dependence on separate flat article-comment presentation.
- Keep child loading incremental and avoid recursive full-feed-card rendering or duplicate interaction requests.

Completion criteria: the same reply has the same author, content, reactions, repost state, and identity in a discussion, profile, or permalink.

### 06 — `feat(storage): stage post images before publication`

- Extend the existing upload-session protocol to support owner-bound staged post images before a public post exists.
- Validate uploaded objects and bind them to a post only on successful final creation. Permit retries without duplicate public posts or duplicate attachment ownership.
- Expire abandoned sessions and reuse existing object-cleanup infrastructure. Publication visibility changes only after the final content is valid.
- Keep existing post image replacement endpoints usable during frontend transition.

Completion criteria: an image-only post can be created without a temporary empty public post, and upload failure leaves a recoverable local draft.

### 07 — `feat(posts): enforce one attachment choice and optional text`

- Add a short-publication-specific validator for either one image gallery or one non-image attachment, with no mixed choices. Enforce it on create, edit, upload completion, and image removal.
- Allow empty text only when the final saved publication has a valid attachment. Validate the final merged state for partial edits; reject removal of the last content from an otherwise empty publication.
- Normalize legacy mixed short-post attachments with a resumable migration: keep the image gallery when present; otherwise retain the first supported non-image attachment. Keep the original descriptors in migration backup/report data.
- Preserve valid single attachments and the article context metadata. Do not silently erase all content from any migrated post.
- Add atomic attachment replacement/removal with current-state conflict handling and safe object cleanup after commit.

Completion criteria: every write path enforces the same final-content rule, and article bodies retain multiple rich blocks.

### 08 — `fix(composer): simplify attachment creation and previews`

- Replace the hidden multi-step attachment form with a clear attachment chooser: images, URL, or publication. Reserve a single choice and provide explicit Replace/Remove controls.
- Show local image thumbnails immediately, per-image removal, upload progress, and recoverable errors; release object URLs when replaced or unmounted.
- Use staged uploads for creation and enable posting when either text or a valid attachment is present. Disable submission during incomplete uploads/resolution.
- Preserve draft text and selected files on failure and avoid duplicate submissions.

Completion criteria: text-only, image-only, and non-image-attachment-only posts can be created through a clear, recoverable UI.

### 09 — `fix(posts): support image and attachment editing`

- Reuse the attachment composer in post/reply editing and show existing images alongside pending replacements.
- Support individual image removal, gallery replacement, removing a whole attachment, and changing attachment type.
- Apply changes on Save; Cancel leaves persisted content intact. Preserve local draft state on conflicts or network failures.
- Update both explicit image descriptors and owned image inventory through the backend operation; merely filtering frontend attachments is insufficient.

Completion criteria: removed images stay removed after reload, cancellation is harmless, and concurrent saves cannot resurrect deleted media.

### 10 — `fix(links): resolve playable resources with card fallback`

- Centralize server-side URL classification for supported resource forms and approved provider embed URLs. Reuse existing public-address and redirect protections for all network resolution.
- Validate provider resource metadata/embeddability where supported. Treat provider homepages, unsupported paths, unavailable content, and uncertain results as cards rather than blindly constructing iframes.
- Return a typed player-or-card result and let the composer/editor consume it. Never embed arbitrary provider-supplied HTML or a client-forged iframe URL.
- Preserve already saved URLs and provide a readable card fallback when resolution fails. Provider playback may still change later; do not claim metadata guarantees permanent playback.

Completion criteria: a homepage such as `https://soundcloud.com` becomes a link card; a supported, confirmed resource can become a player.

### 11 — `feat(links): cache previews in a background worker`

- Reuse the bounded fetcher in a focused `links` resolver and add title, description, site name, preview image, and validated player metadata.
- Use the existing Redis service for cached results and a durable job mechanism with acknowledgment, retries, and deduplication. Define pending/ready/fallback states, expiry, negative caching, and bounded concurrency.
- Add a separate `link-preview-worker` Docker Compose service using the backend image. Keep network extraction outside publication-save transactions and feed request handling.
- Enqueue on URL attachment creation/change and cache miss; schedule existing URL attachments for lazy or explicit backfill. Read persisted posts even when the worker is unavailable.
- Apply the existing SSRF protections to redirects and any fetched thumbnail/provider data. Bound response size and timeout, and use a fixed provider allowlist for embed metadata.
- Document worker startup, development mode, cache/queue recovery, and configuration. Update `uv.lock` only if Python dependencies change.

Completion criteria: repeat URLs reuse cached metadata; stalled/retried jobs do not create duplicate work or prevent posting and reading.

### 12 — `feat(previews): display resolved cards and players automatically`

- Connect the composer, saved attachments, and article nodes to cached resolver results, with bounded pending-state refresh and cancellation of outdated URL requests.
- Render available card metadata immediately and refresh stale metadata without blanking the card. Provide a stable hostname/link fallback.
- Instantiate validated players on approaching the viewport and remove the application-level load-player button; retain provider playback controls and an external-link fallback.
- Batch/deduplicate metadata reads for repeated URLs in feeds and avoid an unbounded polling loop.

Completion criteria: readers see cards or ready player controls without a separate activation step, and a cold cache or offline worker remains usable.

### 13 — `fix(editor): preserve selection and improve block controls`

- Match the reference's insertion gaps, before/between/end placement, slash menu, contextual deletion, and keyboard-accessible block controls.
- Preserve selection and intended insertion position while menus, link dialogs, and file pickers take focus. Restore the caret to an editable position after inserting atomic nodes.
- Add a drag destination indicator, correct position mapping for moves in both directions, and keyboard movement. Group each logical change into a coherent undo step.
- Position selection formatting and menus correctly during scrolling/resizing and keep them within the viewport.

Completion criteria: formatting affects the intended selection; blocks insert and move at the indicated position; undo/redo restores the document coherently.

### 14 — `fix(editor): preserve rich content through editing and saving`

- Align supported quote attribution, code language, alignment, image, link-card, and player behavior with the reference and the current article schema.
- Update TipTap extensions, editable node views, JSON conversion, backend validation, and read-only rendering together for any supported attributes that change.
- Integrate the cached link resolver, image previews, replacement/removal, and upload retry state without resetting user selection or overwriting intervening edits.
- Keep article cover changes and inline image operations distinct. Normalize loaded legacy nodes and preserve existing content through save/reopen.
- Avoid whole-document resets on routine editor transactions; keep draft state synchronized with explicit save/publish actions.

Completion criteria: editing, saving, reopening, and reading retain supported rich content and attributes, with summary generation reflecting the saved body.

### 15 — `fix(gallery): match carousel and image viewer design`

- Replace the grid with a horizontal scroll-snap carousel, a visible next-slide edge, position indicator, and bounded previous/next controls.
- Support touch scrolling, keyboard navigation, resize behavior, and reduced motion.
- Match the reference's lightweight image popup: contained image, light blurred backdrop, external close control, hover/focus navigation, and visible controls on touch devices.
- Open the selected slide; on close, synchronize the carousel position and restore focus and prior page scrolling. Support Escape and backdrop close without closing on navigation clicks.
- Handle a single image, image-load errors, and gallery changes while the viewer is open.

Completion criteria: all gallery images are reachable in the feed and viewer, and the active image stays consistent between them.

## Implementation and deployment discipline

- Implement commits in the listed order. Steps 02–04 form a coordinated backend migration rollout: additive code first, then a maintenance window with writes paused, migration, and new-storage cutover. Do not expose a partly migrated dataset.
- Before the migration window, back up the database and prepare the restore procedure. Execute the user-authorized data conversions with writes paused. If reconciliation checks are separately requested, compare mappings, relationships, reactions, counts, and visibility. Successful migration command completion is an operational result, not a claim that application behavior or rollback recovery has been tested.
- Rollback before new writes can restore the pre-cutover backup. Rollback after accepting new writes requires reconciliation/export of those writes; an old backup alone is not a lossless rollback.
- Review and update `README.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/INTERACTIONS.md`, and `docs/DEMO.md` as applicable within each change. Update seed/demo data with the relevant contract change, without overwriting owner-edited fixtures.
- Keep endpoint descriptions, request/response examples, and OpenAPI/Scalar documentation consistent with each API change. Reviewing their source is part of implementation; generating or serving documentation for verification follows the repository's check policy.
- Use English source, documentation, comments, and complete backend docstrings. Keep application wiring in `main.py` minimal and routine database operations in Beanie.
- Do not add or run tests, builds, linters, automated verification, or manual application verification until the user requests checks. The completion criteria above are planned acceptance scenarios, not claims that they have been exercised.
- When checks are requested, prioritize migration resumption/collisions, long legacy replies, visibility after deletion/unpublishing, concurrent attachment edits, image-only retry paths, provider fallback/cache failures, editor round trips, and keyboard/touch gallery behavior. Run local application checks through Docker Compose development mode.
- During implementation, create the corresponding local commits after each coherent change and include related documentation. Split an independently useful discovered fix into its own Conventional Commit when necessary; do not mix it into an unrelated item. Never push without an explicit request.

## Implementation record

The original 15 steps were committed in order:

| Step | Commit |
| --- | --- |
| 01 | `d7496e5` |
| 02 | `6428599` |
| 03 | `86cb405` |
| 04 | `039b10d` |
| 05 | `3f1063d` |
| 06 | `b677d4f` |
| 07 | `3a4a3ec` |
| 08 | `3a57e10` |
| 09 | `2a0c963` |
| 10 | `9850625` |
| 11 | `713ac5a` |
| 12 | `f028583` |
| 13 | `10af476` |
| 14 | `d3bdd1e` |
| 15 | `85050d9` |

Follow-up commits complete draft retry recovery and retained-image handling
(`528bab9`), editor keyboard focus and gallery resize (`cd0ae8d`), the migration
startup guard (`13408a3`), bounded worker recovery and preserved card fallbacks
(`bb44360`), current API examples and valid demo fixtures (`6d3a85a`), development
worker/backup wiring (`217d820`), and cancellation of dismissed attachment lookups
with UTF-8 editor source (`124c9ad`). Legacy `author_id` ownership encountered
during the maintenance run is handled by `f87725c`. No commits have been pushed.

On 2026-11-11, the local maintenance run paused the API and development frontend
and created `data/migration-backups/before-content-20261111T151835Z.archive.gz`.
The summary command updated 13 articles. Discussion conversion reported 37 legacy
post replies, 32 legacy article comments, and 69 completed mappings. These figures
are the mutation commands' own results, not a separate reconciliation run.

Tests, builds, linters, browser checks, and `discussion-report` have not been run.
The acceptance criteria above remain scenarios to exercise when checks are requested.

Attachment normalization initially stopped on three older records with `author_id`
and no `owner_id`. The compatibility fix preserves their original authorship and
legacy field. Resuming the command completed normalization for 116 post records.
Legacy discussion collections and attachment backup checkpoints remain in the
database; the original compressed archive remains available locally.

After conversion, Compose started `api`, `frontend-dev`, and `link-preview-worker`
using existing images with `--no-build`. The API logged application startup complete
and Vite reported ready at `http://localhost:5173`. Startup logs were read to finish
the maintenance operation; no application scenario, build, linter, automated test,
or separate reconciliation command was executed.
