# Content migration operations

The `backend.migrate` command uses the configured database and Redis. Run it through
the backend development image. Back up the database before conversion and pause API
writes (stop `api` and `frontend-dev`) before moving discussions. Run the command with
`docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps --pull never api python -m backend.migrate discussions`.

Deploy the unified discussion code before restarting the API. Do not resume legacy
writes between conversion and cutover. Existing `post_replies`, `article_comments`,
and `comment_likes` remain available for rollback; they are no longer active storage.
The migration truncates synthetic reply text to 280 characters as authorized.

`reply_migration_mappings` preserves old scoped IDs, resolves collisions, and tracks
completion per record. Repeating a conversion resumes it without duplicating posts
or reactions. Source timestamps and tree positions are retained. Legacy likes have
no timestamp field, so their ObjectId generation time supplies the new edge time.

The Redis lock `migration:discussion-posts:v1` has no expiry to prevent overlapping
processes. After a crashed process, confirm it is no longer running before deleting
only that lock and rerunning. Never remove a lock held by an active migration.

When verification is requested, `backend.migrate discussion-report` reports source
and completed-record counts. Also reconcile tree links, likes, unavailable originals,
legacy URLs, and profile ordering before resuming writes. Report mode does not convert
records; normal Beanie initialization may install declared indexes.

Before new writes, rollback can restore the database backup and previous application
version. After new writes, export and reconcile new publications/reactions before any
restore; restoring an old backup alone loses those changes.

Run `backend.migrate summaries` to backfill article previews. It is repeatable and
does not change article timestamps. Conversion invalidates public feed caches.

Run `backend.migrate attachments` with writes paused after discussion conversion.
It first copies legacy `author_id` into missing `owner_id` fields, retaining the
legacy field and timestamps; existing owners are never replaced. Records lacking
both owner and legacy author stop conversion instead of assigning a guessed owner.
Mixed legacy posts retain their image gallery; otherwise their first supported card,
player, or publication is retained. Original descriptors are kept in
`post_attachment_backups`; completed posts are not rewritten on repeat runs.

The API refuses startup while either retained legacy discussion collection has more
records than completed mappings. Fresh databases start normally. This inexpensive
rollout guard prevents exposing an unfinished conversion; it is not a substitute
for relationship and reaction reconciliation. The standalone migration command does
not start the API and remains usable while the guard blocks application startup.
Report mode does not invalidate feed caches or convert records.

## Local maintenance sequence

The commands below reuse existing development images; they do not build images.
The optional backup service requires the local `mongo:8.0` image and never pulls it
automatically. Pause any other application instance or demo writer using the same
database for the whole window. Keep the resulting archive private: it includes
account and session data and is ignored by Git.

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml stop api frontend-dev link-preview-worker
docker compose -f docker-compose.yml -f docker-compose.migrations.yml run --rm --no-deps migration-backup
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-build redis garage
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps --pull never api python -m backend.migrate summaries
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps --pull never api python -m backend.migrate discussions
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps --pull never api python -m backend.migrate attachments
```

Stop at the first unsuccessful command. The backup is a timestamped compressed
MongoDB archive under `data/migration-backups/`; it preserves BSON types and index
metadata. Restore it with MongoDB Database Tools `mongorestore --gzip --archive=...`
into a separate recovery database before a planned rollback. Replacing the live
database requires a separate deliberate restore decision and a compatible code
version; this workflow never automatically drops or restores a database.

After any requested reconciliation and when ready to accept writes, start the
existing images with:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-build api frontend-dev link-preview-worker
```
