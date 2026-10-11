# FastAPI Blog Example

Run FastAPI, MongoDB, and Nginx locally with Docker Compose.

## Start the stack

Install Docker Desktop, then run:

```sh
docker compose up --build
```

The application is available at <http://localhost:8080>, and the API documentation is at <http://localhost:8080/docs>. MongoDB is available from the host at `localhost:27017`.

MongoDB files are stored in `./data/mongo` next to this project. This is a project-relative bind mount, so Docker Compose does not place the database in its managed volumes directory (which may be on the system drive). The directory is created when the stack starts and is excluded from Git.

## Stop the stack

```sh
docker compose down
```

Stopping the containers keeps the database files in `./data/mongo`. To remove the database, stop the stack and delete that directory manually.
