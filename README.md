# FastAPI Blog Example

A demo microblog built with FastAPI, MongoDB, Redis, React, and Garage.

## Features

- Public profiles and feeds, with a following feed for signed-in users.
- Publication-page discussions with complete reply ancestry and automatic author-thread previews and reading pages.
- Short posts with images and rich-text articles with drafts and scheduled publishing.
- Likes, saves, reposts, and discussions.
- Unlimited owner-only archives and up to five profile pins shared across posts, replies, and published articles.
- Profile editing and active session management.
- Public full-text search across people, posts, articles, replies, and comments, with linked Unicode hashtags.

The shared footer links to the [GitHub repository](https://github.com/serh11chyrva/fastapi-blog-example),
the API reference at `/api/docs`, and the public `/legal` page. The short Legal disclaimer covers the
[MIT license](LICENSE), demo warranties, session cookies, MongoDB Atlas, external content, and independent forks.

## Start the application

Run the commands from the repository root in PowerShell with Docker Desktop running. If you need an `.env` file, copy the example.

```powershell
Copy-Item .env.example .env
```

1. Set `MONGODB_URL` in `.env` to your MongoDB Atlas connection string. Grant the database user the `readWrite` role on the database named by `MONGODB_DATABASE` (default `blog`) and allow your public IP in Atlas. [Atlas connection guide](https://www.mongodb.com/docs/atlas/connect-to-database-deployment/)
2. Place the MaxMind GeoLite2 City database at `data/GeoLite2-City.mmdb`.

### Develop with hot reload

```powershell
docker compose up -d redis garage
docker compose -f docker-compose.yml -f docker-compose.dev.yml build api frontend-dev
.\scripts\setup-storage.ps1 -Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api frontend-dev link-preview-worker
```

Open the [app](http://localhost:5173) or the [API reference](http://localhost:5173/api/docs).

Before starting this version against existing discussion data, follow [the migration runbook](docs/MIGRATIONS.md). The API refuses an unfinished discussion conversion. For later sessions, repeat the last command. Rebuild the affected image when its dependencies or build configuration change. To stop only the app and keep Redis and Garage running, use `stop api frontend-dev link-preview-worker` with the same Compose files.

### Run the Nginx stack

```powershell
docker compose build api
.\scripts\setup-storage.ps1
docker compose up -d --build
```

Open the [app](http://localhost:8080) or the [API reference](http://localhost:8080/api/docs).

To serve the static build alongside Vite, build it with `docker compose build nginx`, then run `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d nginx`.

### Load demo data

Once the API is ready, run the seed in either mode.

```sh
docker compose exec -T api python -m backend.seed
```

Sign in as `alice@example.com` with the configured `DEMO_PASSWORD` (sample value `DemoPassword123!`). See the [demo feature tour](docs/DEMO.md) for more accounts and scenarios.

### Stop the stack

Use `docker compose down` for the Nginx stack, or include both Compose files for development.

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

## Preview the API design without Docker

With Python 3.13 or newer and `uv` installed, run:

```sh
uv sync
uv run uvicorn backend.api.preview:app --host 127.0.0.1 --port 8000 --reload
```

Scalar loads its assets from a CDN. To try the application endpoints, start the full stack. [Scalar reference](http://localhost:8000/api/docs) · [OpenAPI schema](http://localhost:8000/api/openapi.json)

## Documentation

- [API guide](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Interactions and discussions](docs/INTERACTIONS.md)
- [Search behavior and Atlas index setup](docs/SEARCH.md)

Search requires an explicit one-time backfill and Atlas Search index setup; follow
the [search maintenance sequence](docs/SEARCH.md#initial-setup-and-maintenance) before
using `/search`. Missing indexes affect search only and do not block application startup.

### Link metadata worker

Start the background preview resolver with the development services:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api frontend-dev link-preview-worker
```

The worker uses the backend image; rebuild that image only for dependency or build
changes. Restart `link-preview-worker` after changing worker Python code. Redis now
uses AOF persistence in `redis-data` for queued URLs and cached metadata. Do not remove
that volume during routine restarts. Missing/stale URLs enqueue automatically; existing
saved links are resolved lazily when displayed. Worker downtime leaves usable link
cards and does not block publication saves. Four fetches run concurrently, each bounded
by 20 seconds, with at most three attempts per queued failure. Cached metadata refreshes
after six hours and remains usable for one day. A failed refresh preserves the last
ready card without extending its one-day expiry. Fallback results expire after five
minutes. Metadata now uses v2 cache keys; when updating from v1, restart `api` and
`link-preview-worker` together with both Compose files. Old keys expire naturally;
no MongoDB migration or Redis volume reset is required.
