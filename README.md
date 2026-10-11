# FastAPI Blog Example

Run FastAPI, MongoDB, Redis, Nginx, and Mongo Express locally with Docker Compose.

## Configure and start

Copy `.env.example` to `.env` if you do not already have a local `.env` file:

```powershell
Copy-Item .env.example .env
```

The sample development configuration is:

```dotenv
MONGO_ROOT_USERNAME=blog_admin
MONGO_ROOT_PASSWORD=localmongopassword123
MONGODB_DATABASE=blog
MONGO_PORT=27017

API_PORT=8080

MONGO_EXPRESS_PORT=8081
MONGO_EXPRESS_USERNAME=admin
MONGO_EXPRESS_PASSWORD=localuipassword123

REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
```

These credentials and settings are for local development only. Keep MongoDB passwords URL-safe (letters and numbers), or percent-encode reserved characters in the MongoDB connection URI.

Start the stack:

```sh
docker compose up --build
```

- App and API docs: <http://localhost:8080> and <http://localhost:8080/docs>
- Mongo Express database browser: <http://localhost:8081>
- MongoDB: `localhost:27017`
- Redis: `localhost:6379`

Mongo Express credentials are `MONGO_EXPRESS_USERNAME` and `MONGO_EXPRESS_PASSWORD` from `.env`. MongoDB and the web tools are bound to localhost. MongoDB uses the root credentials from `.env`; do not expose these ports to a network or use this configuration in production.

Redis is provided as a local cache service with persistence disabled. The API receives its connection URL through `REDIS_URL`; the application does not use Redis yet.

MongoDB files are stored in `./data/mongo` next to this project, outside Docker-managed volumes. The directory is created when the stack starts and is excluded from Git.

## Stop the stack

```sh
docker compose down
```

Stopping the containers keeps MongoDB files in `./data/mongo`. To reset the local database, stop the stack and delete that directory manually.
