# Content migration operations

The `backend.migrate` command uses the configured database and Redis. Run it through
the backend development image. Back up the database before conversion and pause API
writes (stop `api` and `frontend-dev`) before moving discussions. Run the command with
`docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps api uv run python -m backend.migrate discussions`.

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
