# Repository Instructions

## Language

- Write all source code, documentation, docstrings, and comments in English.

## Application Structure

- Keep application code under `src/fastapi_blog_example/`.
- As the application grows, organize routers, services, models, and configuration in separate package areas. Keep `main.py` focused on application creation and wiring.
- Keep modules focused and avoid introducing layers that do not support a concrete feature.

## MongoDB

- Use Beanie for MongoDB document models and routine database operations.
- Use Motor directly only when Beanie does not provide the needed operation or when an integration requires Motor.

## Dependencies and Checks

- Manage Python dependencies with `uv`; keep `uv.lock` in sync with dependency changes in `pyproject.toml`.
- Add or run tests, builds, linters, or other verification checks only when the user asks.

## Git Workflow

- Group unrelated changes into logically separate commits and suggest clear commit messages.
- Never push commits unless the user explicitly asks.
