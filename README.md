# Commonplace

A local demonstration microblog built with FastAPI, Beanie, MongoDB, Redis, React, Tailwind CSS, TipTap, Nginx, and Garage S3-compatible object storage.

## Start the application

Copy the sample local configuration if you do not already have an `.env` file:

```powershell
Copy-Item .env.example .env
```

Start the services from the repository root:

```sh
docker compose up --build -d
```

The first startup configures MongoDB as a single-node replica set and creates a least-privilege application database user. The setup is idempotent and keeps the existing `./data/mongo` directory. Garage stores avatars under `./data/garage`.

Seed the public demo profiles, posts, articles, follows, and badges:

```sh
docker compose run --rm api python -m backend.seed
```

Open the app and API documentation:

- App: <http://localhost:8080>
- API docs: <http://localhost:8080/api/docs>
- Mongo Express: <http://localhost:8081>

Demo accounts are `alice@example.com`, `ben@example.com`, and `casey@example.com`. Their local-only password is the value of `DEMO_PASSWORD` in `.env` (the sample is `DemoPassword123!`). You can also register a new account in the app.

MongoDB and Redis ports are bound to localhost for development. When connecting to the replica set from a host-side MongoDB client, use a direct connection, for example `mongodb://localhost:27017/?directConnection=true`. Mongo Express connects within the Compose network.

## Features

- Email or `@username` registration and login with opaque, server-side sessions.
- A session settings page with IP, User-Agent, last activity, individual revocation, and logout from other sessions.
- Append-only audit events for security, profile, follow, and publication actions.
- Public profiles with bios, links, assigned demo badges, and uploaded JPEG, PNG, or WebP avatars.
- Follow relationships and chronological public and following feeds.
- 280-character micro-posts and TipTap article drafts that can be published and edited.
- Responsive English UI; published content and profiles are readable without signing in.

Likes, reposts, threaded micro-post replies, flat article comments, email delivery, OAuth/OIDC, and MFA are planned follow-up features.

## Architecture

- Backend code lives under `src/backend/`. Authentication, profiles, content, and audit each keep their Beanie documents in their domain package; repositories own common persistence queries and services hold reusable domain behavior.
- `main.py` wires FastAPI, the async PyMongo client used by Beanie, Redis, and Garage. MongoDB is the source of truth; audited writes use replica-set transactions.
- Passwords use Argon2id. Existing scrypt hashes are checked and upgraded after a successful login.
- Frontend source lives under `src/frontend/`. Docker uses a Node.js build stage with cached npm dependencies, Vite production minification and separate React/editor chunks, then copies only static output into Nginx.
- Tests are grouped by layer: `tests/unit/`, `tests/services/`, and `tests/api/`.

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

Stopping the services keeps MongoDB and Garage data. The sample credentials and single-node storage configuration are for local development only; replace secrets and use an appropriately secured deployment before exposing the app to a network.
