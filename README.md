# Commonplace

A demonstration microblog built with FastAPI, Beanie, MongoDB Atlas, Redis, React, Tailwind CSS, TipTap, Nginx, and Garage S3-compatible object storage.

## Preview the API design without Docker

Run from the repository root with Python 3.13 or newer and `uv` installed:

```sh
uv sync
uv run uvicorn backend.api.preview:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://localhost:8000/api/docs> (or `/`, which redirects there). The raw schema
is available at <http://localhost:8000/api/openapi.json>. This standalone preview
requires no Docker, MongoDB, Redis, Garage, GeoIP database, or `.env` configuration.
Python dependencies must still be installed. Scalar loads its browser assets from
a CDN, so viewing the reference requires internet access.

The preview generates the complete contract from the application's current routes,
including models, authentication, examples, and upload descriptions. Scalar's request
testing and client buttons are hidden. Only the reference, schema, and root redirect
are served; application endpoints (including uploads, image downloads, and `/health`)
return 404. Examples describe the full application, not a running backend or mock data.
Use the full stack below to execute API operations.

## Start the application

Copy the sample configuration if you do not already have an `.env` file:

```powershell
Copy-Item .env.example .env
```

Configure MongoDB Atlas before starting the services:

1. Create an Atlas cluster and a database user with the `readWrite` role for the database named by `MONGODB_DATABASE` (default: `blog`).
2. Add the public outbound IP of the machine running Docker to the Atlas project's IP access list.
3. Copy the connection string from the cluster's **Connect > Drivers** dialog and set `MONGODB_URL` in `.env`, replacing the username and password. Percent-encode reserved characters in credentials.

```dotenv
MONGODB_URL='mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority'
MONGODB_DATABASE=blog
```

Use the actual Atlas connection string, preserving its connection options. `MONGODB_DATABASE` selects the application's database independently of the URI's default database. The application requires transaction support for audited writes. Both Compose and the backend require a non-empty `MONGODB_URL`; there is no default local MongoDB connection. For a backend launched outside Docker, export these variables in its process environment; the backend does not load `.env` automatically.

See the official [Atlas connection guide](https://www.mongodb.com/docs/atlas/connect-to-database-deployment/) and [connection string formats](https://www.mongodb.com/docs/manual/reference/connection-string/).

Provision the two private Garage image buckets before starting the API. Run from the repository root (Docker Desktop must be running):

```powershell
docker compose build api
.\scripts\setup-storage.ps1
```

The idempotent script starts Garage, ensures `blog-avatars` and `blog-publications` exist, grants the configured key access, and configures upload CORS. It reads `GARAGE_ACCESS_KEY` from the process environment or `.env`; `-AccessKey` can override it. Repeat provisioning after removing Garage data. The API requires both buckets on startup and in `/health`.

The upload CORS rule allows the lower-case header name `content-type`, matching browser preflight requests. Garage compares allowed header names literally; using `Content-Type` here causes browser uploads to be rejected before PUT. The provisioning script runs the current workspace CORS setup code inside the API image, so repeating setup also applies CORS fixes without an image rebuild.

Place a MaxMind GeoLite2 City database at `data/GeoLite2-City.mmdb` before starting the API with Compose. Compose mounts this file read-only at `/data/GeoLite2-City.mmdb`; it is not bundled into the image. Replace the file with an updated database and restart the API to reopen it. Outside Docker, the default path is `data/GeoLite2-City.mmdb` relative to the working directory; `GEOIP_CITY_DB_PATH` can override it. If the backend cannot open or query the database, session locations display `Unknown location` and authentication remains available. Compose requires the host file to exist for its bind mount.

Start the remaining services:

```sh
docker compose up --build -d
```

For development with automatic code updates, use the development override instead:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d api frontend-dev
```

Open <http://localhost:5173>. Changes under `src/backend/` restart the API worker automatically, and frontend changes under `src/frontend/` are applied by Vite without rebuilding or restarting containers. The Vite server proxies `/api` and `/static/images` requests to the API container. The development override sets `APP_ORIGIN` to `FRONTEND_DEV_ORIGIN` (default: `http://localhost:5173`). This mode keeps Redis and Garage in Docker, connects to MongoDB Atlas using the same settings, and does not start Nginx unless it was already running.

To return to the regular Nginx setup, run:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml stop frontend-dev
docker compose -f docker-compose.yml up -d api nginx
```

On startup, Beanie initializes the application's document models and indexes in the configured Atlas database. Database users and cluster access are managed in Atlas. Garage stores all image objects and its metadata under `./data/garage`.

If upgrading from the previous local MongoDB stack, add `MONGODB_URL` to your existing `.env` and remove the obsolete `MONGO_ROOT_*`, `MONGO_APP_*`, `MONGO_REPLICA_KEY`, `MONGO_PORT`, `COMPASS_WEB_*`, and any legacy `MONGO_EXPRESS_*` variables. Remove the previous containers before starting the updated stack:

```sh
docker compose down --remove-orphans
```

This preserves the old `./data/mongo` directory and named volumes. Existing local MongoDB data is not migrated to Atlas automatically; export/import it separately if needed. The updated stack does not run MongoDB, replica-set initialization, or Compass Web containers.

Seed the public demo profiles, posts, articles, follows, and badges:

```sh
docker compose run --rm api python -m backend.seed
```

Open the app and API documentation:

- App: <http://localhost:8080>
- API docs: <http://localhost:8080/api/docs>

Demo accounts are `alice@example.com`, `ben@example.com`, and `casey@example.com`. Their local-only password is the value of `DEMO_PASSWORD` in `.env` (the sample is `DemoPassword123!`). You can also register a new account in the app.

The Redis port is bound to localhost for development. MongoDB is accessed remotely through the configured Atlas connection string.

Image bucket names and size limits are defined in `src/backend/core/config.py`: `blog-avatars` contains avatars; `blog-publications` contains post images, article covers, and inline images. Avatars, post images, and inline article images allow 5 MiB per file; covers allow 10 MiB. Temporary uploads live under `temporary/` in the corresponding private bucket. Neither bucket is exposed as a public website.

Browsers request ten-minute presigned PUT URLs, upload directly to Garage, then confirm through the API. Confirmation validates a separate final copy and attaches it transactionally; upload replay cannot change an accepted image. API responses use `/static/images/...` URLs. FastAPI checks publication visibility before serving images, including private drafts. Nginx and Vite forward these paths to FastAPI. See [docs/API.md](docs/API.md) for the complete protocol.

`S3_ENDPOINT_URL` is the internal address (`http://garage:3900` in Docker); `S3_PUBLIC_ENDPOINT_URL` is the browser-reachable address used when signing URLs (`http://localhost:3900` locally). Garage's S3 port is bound to localhost via `S3_PORT`. If you change that port, update the public URL as well. `STORAGE_CORS_ORIGINS` is a comma-separated list of allowed frontend origins, defaulting to ports 8080 and 5173. Keep it aligned with `APP_ORIGIN`, `API_PORT`, and the development frontend origin when customizing ports. For a remote deployment, configure a browser-reachable HTTPS S3 endpoint and its network exposure; the local port binding alone does not provide remote access. Signed URLs must reach Garage with their original host and path.

A worker runs every minute to remove replaced images and retry failed deletions. Temporary files and abandoned final copies become eligible after an hour (temporary files after URL expiry plus one hour). Upload-session records expire seven days after their upload deadline; cleanup jobs remain until handled. Dependency changes use `uv`; configuration defaults require restarting the development backend or rebuilding the production API image.

### Reset existing application data

Legacy media routes and multipart uploads are removed. There is no migration of existing files or embedded article URLs. Clearing local `data/` removes Garage objects and old local MongoDB files; it does **not** clear the configured MongoDB Atlas database.

For a complete fresh start, stop the API and frontend services, provision storage, then explicitly erase only the configured application database and its two image buckets. This deletes accounts, publications, and sessions in that database:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml stop api nginx frontend-dev
docker compose run --rm --no-deps api python -m backend.storage.reset --confirm-database blog
docker compose up -d
docker compose run --rm api python -m backend.seed
```

Replace `blog` with your exact `MONGODB_DATABASE`. Never run reset automatically at startup. Provisioning and reset are separate operations; reset keeps the Garage bucket configuration.

## Features

- Email or `@username` registration and login with opaque, server-side sessions.
- A session settings page with web/mobile/desktop client types, approximate GeoLite2 locations, readable browser/device labels, last activity, individual revocation, and logout from other sessions.
- Append-only audit events for security, profile, follow, and publication actions.
- Public profiles with bios, versioned links with domain detection and independent redirects, shared badge definitions with versioned display payloads, and uploaded JPEG, PNG, or WebP avatars.
- Own-profile API and settings with private badge preferences, server-enforced visibility, and revision checks that reject stale profile edits.
- Follow relationships and chronological public and following feeds.
- 280-character micro-posts with up to five JPEG, PNG, or WebP images and UUID-suffixed share links; TipTap articles support a cover image, inline images, drafts, immediate publishing, and scheduled publishing.
- Editorial black-and-white UI with separate Posts and Articles profile tabs; article editing and reading use a full-screen writing and reading layout.
- Responsive English UI; published content and profiles are readable without signing in.

Likes, reposts, threaded micro-post replies, flat article comments, email delivery, OAuth/OIDC, and MFA are planned follow-up features.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for module responsibilities, transaction and upload guarantees, pagination, and frontend boundaries.

- Backend code lives under `src/backend/`. The `api/` package owns all HTTP endpoints, the `/api` and `/v1` router hierarchy, shared OpenAPI documentation, and the standalone reference preview. Authentication, profiles, content, and audit each keep their Beanie documents in their domain package; repositories own persistence queries, services own audited publication operations, and presenters map documents to API responses using an already loaded author. Feed loading and opaque cursors live outside HTTP routers.
- Upload preparation, leasing, copying, and completion live in `storage/service.py`; target ownership and domain attachment changes live in `storage/attachments.py`. Saved results are parsed into the response model selected by the immutable upload purpose.
- Profile mutations, read assembly, and response presenters are separate modules. Follower/following and own-article lists use bounded offset pagination. Image attachment lookups have explicit indexes in the Beanie document models.
- `links/` resolves saved redirects independently of profile handles. Profiles keep embedded link identities and badge assignments; the shared `badge_definitions` catalog owns badge display and policy. Startup migrates older profile records once, preserving link IDs. Links use format version 1, badges version 2; profile PATCH requests require the revision from `GET /api/v1/me/profile`. See the API guide for compatibility and migration details.
- Infrastructure clients are held in a typed `AppResources` container. HTTP dependencies produce transport-independent audit metadata; audit writes live in `audit/`. Authentication dependencies, rate limiting, and password operations live in `auth/`.
- Audited transactions report concurrent write conflicts as 409 without replaying the operation automatically. Database failures return 503; clients should reload before retrying an uncertain write.
- `main.py` wires FastAPI, the async PyMongo client used by Beanie, Redis, and Garage. MongoDB is the source of truth; audited writes use replica-set transactions.
- The public feed cache version advances on API startup so deployments and explicit data resets do not reuse cached responses with obsolete image URLs.
- Passwords use Argon2id. Existing scrypt hashes are checked and upgraded after a successful login. API hashing and verification run in a dedicated pool limited to four concurrent operations per process, keeping the event loop available.
- Account registration/login and session persistence/revocation are application services. Authentication routers retain HTTP cookies, request metadata, and rate-limit enforcement.
- Session activity uses conditional field updates and a monotonic last-seen timestamp. Concurrent activity cannot clear revocation or extend the absolute session deadline.
- Session client type and optional native-app device name are saved at registration/login; older sessions default to web. IP and User-Agent stay internal. `auth/presentation.py` formats public location and device labels, using an application-owned GeoLite2 reader and User-Agent parsing off the event loop.
- Protected frontend routes wait for session restoration before redirecting. Public profile contracts exclude account email and private badge settings; publication pages cancel stale requests when their address changes.
- Frontend source lives under `src/frontend/`. `app/` owns a single route tree, layouts, and explicit authentication states; `features/` owns pages and editor workflows, including session settings under `features/profiles/sessions/`; `shared/` owns API contracts, transport, upload handling, pagination hooks, and common UI. Article editing logic lives in a dedicated hook. Lists expose load-more controls, cancel stale requests, and distinguish loading failures from empty results. API errors retain their HTTP status and details. Docker uses a Node.js build stage with cached npm dependencies, Vite production minification and separate React/editor chunks, then copies only static output into Nginx.
- `docker-compose.dev.yml` mounts API and frontend source for reload/HMR during development; the default Compose setup continues to serve the production frontend from Nginx.
- Tests are grouped by layer: `tests/unit/`, `tests/services/`, and `tests/api/`.

## API reference

The interactive Scalar API reference is available at `/api/docs` and the raw schema at `/api/openapi.json`. Scalar telemetry and its optional AI agent are disabled. Operation summaries, errors, examples, and tags live beside the routes; cookie security comes from authentication dependencies, and Origin is an explicit header annotation. Shared OpenAPI generation only adds schema-derived examples. See [docs/API.md](docs/API.md) for endpoint tables, authentication and cookie handling, request/response examples, pagination, upload rules, and common errors.

## Development checks

Python dependencies are managed with `uv`:

```sh
uv sync --all-groups
uv run pytest
```

Frontend dependencies are managed with npm:

```sh
cd src/frontend
npm ci
npm run build
```

Use Node.js 22.12 or newer for local frontend builds, matching the Node.js version used by the Docker build.

## Stop the stack

```sh
docker compose down
```

Stopping the services keeps Atlas data and local Garage data. The sample application and Garage credentials and single-node object storage configuration are for local development only; replace secrets and use an appropriately secured deployment before exposing the app to a network.
