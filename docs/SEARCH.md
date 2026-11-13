# Public search and hashtags

Search is available to guests and signed-in readers at `/search`, between Explore
and Following in desktop and mobile navigation. The discovery sidebar submits to
the same page. Query and publication sort are stored in the URL, for example
`/search?q=fastapi&sort=relevance`.

## Matching and presentation

Search runs after 300 ms without input, or immediately on Enter. Empty or
one-character ordinary input shows a prompt. Queries accept at most 200 Unicode
characters. Every word must match somewhere in the searched fields. Matching
ignores case and performs no language-specific stemming. The last word supports
prefixes; words of at least four characters allow one typo. Text uses the standard
analyzer, usernames use keyword autocomplete,
and `stableTfl` similarity keeps relevance scores consistent across search nodes.
Username matches rank above names and biographies, with an extra exact-username
boost. Article titles have more weight than body text.

Hashtags are mandatory exact filters: `fastapi #python` requires text and the
`python` tag. Multiple tags must all be present. Tag-only queries are valid,
including a one-character tag. Ordinary `python` also finds text without a tag.
A leading `@` is optional for username input. Queries are literal terms, never
Atlas query-language expressions.

People appear first, initially at most three cards with avatar, public name,
username, and biography. Show more appends ten at a time; Show less collapses to
three without discarding loaded cards. Below is a combined list of posts, articles,
replies, and comments, twenty per page. Reposts do not duplicate originals.
Relevance is the default; Latest orders by original publication time. Dates and
unique projection IDs break relevance ties. The blocks have independent loading,
empty, retry, and continuation state. A new query resets both; sort resets publications.

Hashtags link to `/search?q=%23tag` in posts, replies, article titles and text,
previews, biographies, and public names. Tags contain one to 64 Unicode letters,
numbers, combining marks, or underscores. Comparison uses NFC and Unicode case
folding; rendering preserves saved spelling. HTTP URLs and rich-text code/link
marks do not create tags. Formula sources produce neither searchable text nor tags.
Structured hashtag nodes and attachments remain supported.
TipTap decorations recognize tags across formatting without changing saved JSON.
Editing shows the decoration without navigating; read-only views provide links.

## Data flow and consistency

`search/` owns the Beanie projection, extraction, queries, repository, responses,
backfill, and Atlas index management. `publications/hashtags.py` owns the backend grammar.

`search_publications` has one unique `(source_kind, source_id)` entry per eligible
post or published article, including publication-backed discussion entries. It
stores complete text, title, normalized tags, and original publication time.
Truncated summaries, attachment metadata, referenced publication content, email,
and private account settings are not indexed. The user index contains username,
public name, biography, derived `search_hashtags`, and ID for ordering.

Content and archive mutations maintain projections in the source transaction with
the audit event. This covers staged-post publication, discussion creation, scheduled
publishing, and demo fixtures. Account/profile writes derive profile tags in their
own transaction. Atlas index provisioning is not required for canonical writes.

Indexing is eventually consistent: new or edited content can take time to match;
an old text match can temporarily select an updated publication. Results always
hydrate current canonical records. Visibility, discussion originals and archived
ancestors, and author existence are checked **before the page limit**. Deleted
posts, pending uploads, drafts, scheduled articles, and archives are excluded for
every viewer, including the owner. Deleted ancestors retain existing tombstone
semantics. An unavailable discussion original hides its replies. Ancestor archive
changes do not rewrite all descendant projections.

Article `search_enabled` defaults to true, including when the field is absent from
legacy documents. Creating or updating an article with `search_enabled: false`
excludes that article from internal text and hashtag search. The setting leaves
feeds, public profiles, direct links, and external search-engine indexing unchanged.
It does not independently hide comments; disabling `comments_enabled` hides the
whole discussion, including its search results, for every viewer.

An article search opt-out removes its own projection in the content transaction.
Re-enabling upserts the projection when the article is published and unarchived;
normal Atlas indexing delay still applies. Candidate hydration also checks the
current source field before pagination, so a stale indexed projection cannot return
an opted-out article. Discussion closure is likewise checked through the current
original article without rewriting descendant projections. No new index or backfill
is required for these settings.

Article excerpts contain at most 280 characters from current body text near a
literal/prefix match. Fuzzy-only matches without a literal passage use the usual
summary. No card or passage is copied from Atlas highlight output. Cached link
metadata is hydrated after authorization, as for ordinary feeds.

Each endpoint checks its versioned index for queryability. Missing indexes,
unsupported deployments, query timeouts, and unavailable search return 503.
Search readiness does not block API startup or unrelated features. Search does not
cache results in Redis. Atlas continuations use `searchAfter`; API cursors bind
normalized query, result kind, sort, and index version. Cursors are not snapshots
of concurrent edits.

## API

Both endpoints are public. Invalid query/sort/limit/cursor returns 422; unavailable
search returns 503 with the standard `{ "detail": "..." }` envelope. Complete
endpoint and field descriptions and examples are declared in `/api/docs` schemas.

| Endpoint | Parameters | Response |
| --- | --- | --- |
| `GET /api/v1/search/users` | Required `q`; optional `cursor`; `limit` defaults to 3, range 1–50 | `{ "items": [public profile with bio], "next_cursor": string or null }` |
| `GET /api/v1/search/publications` | Required `q`; `sort=relevance` or `latest`; optional `cursor`; `limit` defaults to 20, range 1–50 | `{ "items": [{ "publication": existing post/article feed card, "excerpt": string or null }], "next_cursor": string or null }` |

Examples: `/api/v1/search/users?q=%40ali&limit=3` and
`/api/v1/search/publications?q=fastapi%20%23python&sort=latest&limit=20`.
User continuation requests can change `limit` from 3 to 10; cursors do not bind page size.

## Initial setup and maintenance

Use the existing Atlas database with Search and `searchAfter` support (MongoDB
7.0.5 or newer). Its database user needs Search index management privileges; the
configured Atlas `readWrite` role provides them. No additional service or Python
dependency is needed. Rebuild `frontend-dev` once for the explicit, already used
`@tiptap/pm` dependency declaration.

Pause every writer against this database, including other application instances
and seed processes. Stopping `api` also stops its embedded publication scheduler.
Keep Redis and Garage running. Use the existing backup procedure in
[MIGRATIONS.md](MIGRATIONS.md) before maintenance.

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml stop api frontend-dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps --pull never api python -m backend.migrate search
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps --pull never api python -m backend.search.manage setup
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api frontend-dev
```

Backfill upserts by source identity, removes invalid/orphaned projections, and
refreshes profile tags. It preserves source texts, IDs, timestamps, profile revisions,
discussion metadata, and share links. Reruns resume safely after interruption.
Run only one backfill at a time, with all writers paused. Run it after any legacy
content conversion that bypasses current services.

`setup` creates missing `search_publications_v1` and `search_users_v1` indexes,
updates differing definitions, and waits for READY/queryable status. It fails on
an index build failure or timeout (600 seconds by default; override with `--timeout`).
Stop the sequence after an unsuccessful command. Existing indexes can still have
an indexing delay after backfill. API restarts never backfill or provision Atlas indexes.

When inspection is requested, the read-only status command is:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps --pull never api python -m backend.search.manage status
```

The projection is disposable derived data. Application rollback does not require
restoring or deleting canonical content; retained search collections and internal
profile tags can remain unused. No command drops source collections or restores
backups. Operational setup and migration are explicit actions separate from code changes.

## Acceptance scenarios

When verification is requested, cover text beyond an article preview; Cyrillic,
case, prefixes and typos; all user fields; exact and combined hashtags; formatted
and structured tags; three initial people and inline expansion; independent retries;
both sorts and cursor continuity on unchanged data; current passages after edits;
archived originals/ancestors and deleted visibility; mobile/guest navigation; and
interrupted, repeated backfill. Adding or running tests, builds, linters, or application
checks requires a separate user request under the repository instructions.

References: [Atlas pagination](https://www.mongodb.com/docs/search/query/paginate-results/),
[autocomplete mappings](https://www.mongodb.com/docs/search/indexes/field-types/autocomplete-type/),
and [PyMongo indexes](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/indexes/).
