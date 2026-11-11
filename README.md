# FastAPI Blog Example

A demo microblog built with FastAPI, MongoDB, Redis, React, and Garage.

## Features

- Public profiles and feeds, with a following feed for signed-in users.
- Short posts with images and rich-text articles with drafts and scheduled publishing.
- Likes, saves, reposts, and discussions.
- Profile editing and active session management.

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
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api frontend-dev
```

Open the [app](http://localhost:5173) or the [API reference](http://localhost:5173/api/docs).

For later sessions, repeat the last command. Rebuild the affected image when its dependencies or build configuration change. To stop only the app and keep Redis and Garage running, use `stop api frontend-dev` with the same Compose files.

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
