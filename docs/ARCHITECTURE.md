# Application architecture

Backend source lives in `src/backend/`; frontend source lives in `src/frontend/`.
Feature packages own their behavior and persisted models. Shared infrastructure
does not own feature policy.

## Backend responsibilities

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
| `auth/` | Password verification, registration/login, sessions, cookie authentication dependencies, and rate limits |
| `profiles/` | Profile revisions, follows, badge preferences, bounded list reads, and profile presenters |
| `content/` | Publication operations, article validation, presenters, feeds, cursors, and scheduled publishing |
| `storage/` | Upload preparation, confirmation leases, immutable copies, attachment adapters, image serving, and cleanup |
| `audit/` | Transport-independent request metadata and transactional audit event writes |
| `core/` | Configuration, typed clients, transaction conflict policy, application errors, and shared OpenAPI presentation |

`main.py` creates the application, registers boundaries, and manages client and
worker lifetimes. `core/security.py` retains compatibility exports for existing
callers; password and token implementation belongs to `auth/security.py`.

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

Mixed feeds use separate post/article response types discriminated by `kind`.
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
  the prepare, direct PUT, and confirm protocol.

Protected routes wait for session restoration. An unavailable authentication service
has an explicit retry state. Route changes cancel outdated reads, and editor form
state is recreated when the article ID changes. Loading failures remain distinct
from successfully loaded empty lists.

Cookie security is generated from authentication dependencies. Optional-session
reads explicitly allow anonymous access in OpenAPI. Shared schema generation only
adds examples; it does not infer authentication or response policy from URL text.
