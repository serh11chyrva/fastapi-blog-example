# Repository Instructions

## Language

- Write all source code, documentation, docstrings, and comments in English.

## Application Structure

- Keep backend application code under `src/backend/` and frontend application code under `src/frontend/`.
- Organize routers, services, repositories, domain models, and configuration in focused package areas. Keep `main.py` focused on application creation and wiring.
- Keep modules focused and avoid introducing layers that do not support a concrete feature.

## Backend Code Style

- Keep backend code structured into focused classes, functions, and methods with clear responsibilities. Separate logical blocks with blank lines, and follow the existing module organization.
- Add or maintain English docstrings for every backend class, function, and method, including private helpers, nested functions, protocol methods, and configuration classes.
- Start each docstring with a concise description of its purpose. For functions and methods, document every explicit parameter except `self` and `cls` using reStructuredText `:param name:` fields, and document the result using `:return:`. Use `:return: None.` for callables that return no value. Class docstrings should describe their responsibility; document explicit constructor parameters on `__init__`.
- Describe actual behavior, including optional values, ownership or visibility rules, side effects, and transaction guarantees where relevant. Preserve useful existing explanations and update docstrings whenever behavior or signatures change.
- Follow the Ruff configuration in `pyproject.toml`, including the target line width of 120 characters. Run Ruff or other verification tools only when the user requests them, as specified below.

## MongoDB

- Use Beanie for MongoDB document models and routine database operations.
- Use Motor directly only when Beanie does not provide the needed operation or when an integration requires Motor.

## Dependencies and Checks

- Manage Python dependencies with `uv`; keep `uv.lock` in sync with dependency changes in `pyproject.toml`.
- Add or run tests, builds, linters, or other verification checks only when the user asks.

## Documentation

- Review the relevant documentation for accuracy and completeness with every code change, and update it in the same change when needed.
- For API changes, review endpoint and field descriptions, request and response examples, and the generated OpenAPI/Scalar reference at `/api/docs`. Keep them consistent with the implemented behavior.
- Documentation review is required even when the user has not requested tests or other automated checks; it does not authorize running those checks.

## Git Workflow

- Group unrelated changes into logically separate commits and suggest clear commit messages.
- Use Conventional Commits: `<type>[optional scope]: <short imperative summary>` in English.
- Use `feat:` for new features, `fix:` for bug fixes, and `docs:` for documentation-only changes. Use `refactor:`, `test:`, `build:`, `ci:`, `perf:`, `style:`, or `chore:` when appropriate.
- Choose the type that describes the primary change. Include related documentation updates in the feature or fix commit; use `docs:` only when the change is limited to documentation.
- Never push commits unless the user explicitly asks.
