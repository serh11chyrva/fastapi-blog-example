# Commonplace

A demonstration microblog built with FastAPI, Beanie, MongoDB Atlas, Redis, React, Tailwind CSS, TipTap, Nginx, and Garage S3-compatible object storage.

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

Start the services from the repository root:

```sh
docker compose up --build -d
```

For development with automatic code updates, use the development override instead:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d api frontend-dev
```

Open <http://localhost:5173>. Changes under `src/backend/` restart the API worker automatically, and frontend changes under `src/frontend/` are applied by Vite without rebuilding or restarting containers. The Vite server proxies `/api` requests to the API container. This mode keeps Redis and Garage in Docker, connects to MongoDB Atlas using the same settings, and does not start Nginx unless it was already running.

To return to the regular Nginx setup, run:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml stop frontend-dev
docker compose -f docker-compose.yml up -d api nginx
```

On startup, Beanie initializes the application's document models and indexes in the configured Atlas database. Database users and cluster access are managed in Atlas. Garage stores avatars under `./data/garage`.

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

The shared media bucket (`blog-avatars`) and upload size limits are defined in `src/backend/core/config.py`, rather than environment variables. Avatars, post images, and inline article images allow 5 MiB per file; article thumbnails allow 10 MiB. Garage creates the same bucket through `GARAGE_DEFAULT_BUCKET` in `docker-compose.yml`; keep that value aligned with `Settings.avatar_bucket` if renaming the bucket. `.env` holds credentials and settings that vary by deployment, such as connection URLs, ports, and application origin. Changing configuration defaults requires restarting the development backend or rebuilding the production API image.

## Features

- Email or `@username` registration and login with opaque, server-side sessions.
- A session settings page with IP, User-Agent, last activity, individual revocation, and logout from other sessions.
- Append-only audit events for security, profile, follow, and publication actions.
- Public profiles with bios, links, assigned demo badges, and uploaded JPEG, PNG, or WebP avatars.
- Follow relationships and chronological public and following feeds.
- 280-character micro-posts with up to five JPEG, PNG, or WebP images and UUID-suffixed share links; TipTap articles support a cover image, inline images, drafts, immediate publishing, and scheduled publishing.
- Editorial black-and-white UI with separate Posts and Articles profile tabs; article editing and reading use a full-screen writing and reading layout.
- Responsive English UI; published content and profiles are readable without signing in.

Likes, reposts, threaded micro-post replies, flat article comments, email delivery, OAuth/OIDC, and MFA are planned follow-up features.

## Architecture

- Backend code lives under `src/backend/`. Authentication, profiles, content, and audit each keep their Beanie documents in their domain package; repositories own common persistence queries and services hold reusable domain behavior.
- `main.py` wires FastAPI, the async PyMongo client used by Beanie, Redis, and Garage. MongoDB is the source of truth; audited writes use replica-set transactions.
- Passwords use Argon2id. Existing scrypt hashes are checked and upgraded after a successful login.
- Frontend source lives under `src/frontend/`. Docker uses a Node.js build stage with cached npm dependencies, Vite production minification and separate React/editor chunks, then copies only static output into Nginx.
- `docker-compose.dev.yml` mounts API and frontend source for reload/HMR during development; the default Compose setup continues to serve the production frontend from Nginx.
- Tests are grouped by layer: `tests/unit/`, `tests/services/`, and `tests/api/`.

## API reference

The interactive Scalar API reference is available at `/api/docs` and the raw schema at `/api/openapi.json`. Scalar telemetry and its optional AI agent are disabled. See [docs/API.md](docs/API.md) for endpoint tables, authentication and cookie handling, request/response examples, pagination, upload rules, and common errors.

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
