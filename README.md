# VISIT 3

## The new company portal for VIS

The frontend is React with Mantine and the backend is FastAPI.

## Table of Contents

- [Setup](#setup)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [Code Generation](#code-generation)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Database Migrations](#database-migrations)
- [Test Data Seeding](#test-data-seeding)
- [Important Bits](#important-bits)

## Setup

### Prerequisites

- [Docker Engine / Docker Desktop](https://docs.docker.com/get-docker/)
- [mise](https://mise.jdx.dev/) to manage Node, uv, and yarn

Install tools and set up pre-commit hooks:

```bash
mise install
```

### Quick Start

1. Install frontend dependencies:

```bash
cd frontend && yarn install
```

2. Run code generation (gRPC + Orval):

```bash
make
```

3. Start backend + infrastructure:

```bash
docker compose up --build
```

4. Start the frontend (see [Frontend](#frontend)).

5. Open http://localhost:3000.

### Code Generation

`make` generates both gRPC stubs (backend) and Orval API clients (frontend). Run it from the project root whenever `.proto` files or the backend API change.

```bash
make           # generate everything
make clean     # clean generated artifacts
```

### Backend

Docker Compose starts the backend, PostgreSQL, MinIO (S3), Keycloak, and the Notifications API.

```bash
docker compose up --build
```

The backend reloads automatically on file changes. For changes to dependencies or generated code, restart the container.

**Services:**

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| API Docs (OpenAPI) | http://localhost:8000/docs |
| MinIO (S3) | http://localhost:9000 |
| Keycloak | http://localhost:8181 |
| Notifications API | http://localhost:6781 |
| PostgreSQL | localhost:5432 |

### Frontend

You can run the frontend locally or in Docker. Both support hot reload.

**Locally:**

```bash
cd frontend && yarn dev
```

**In Docker:**

```bash
docker compose --profile frontend up --build
```

## Database Migrations

Migrations run automatically when the backend container starts. To create a new migration after model changes:

```bash
docker compose exec backend alembic revision --autogenerate -m "description"
```

To apply or revert manually:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
```

## Test Data Seeding

```bash
docker compose exec backend sh -lc "cd /app && .venv/bin/python scripts/seed_test_data.py"
```

Creates/updates test users (unconfirmed, staff, admin, confirmed company) and companies. The script is idempotent.

## Important Bits

### Backend Architecture

The backend follows a layered pattern: **routes -> services -> repositories**.

- **Routes** (`app/routes/`) handle HTTP concerns only.
- **Services** (`app/services/`) contain business logic. Authorization is enforced via decorators (`@require_staff`, `@require_admin`, etc.) in `app/core/decorators.py`.
- **Repositories** (`app/repositories/`) handle all database access, one repository per domain.

### Scheduled Tasks

Periodic tasks are registered with the `Scheduler` in `app/core/scheduler.py`. To add a task, define an async function and register it in `app/main.py`:

```python
scheduler.add(my_task, interval=3600)  # interval in seconds
```

### Code Formatting

- **Backend**: [Ruff](https://docs.astral.sh/ruff/) (formatter + linter)
- **Frontend**: [Prettier](https://prettier.io/)

Both run automatically as pre-commit hooks via `mise install`. To run manually:

```bash
ruff format backend/        # format
ruff check backend/         # lint
pre-commit run --all-files  # run all hooks
```

### API Routes & Types

- Ensure FastAPI routes are **properly typed** with return types and request body schemas
- Use **meaningful `operation_id`s** -- Orval uses these to generate client function names
- Example:
  ```python
  @router.post("/login", operation_id="loginUser")
  async def login(request: LoginRequest) -> TokenResponse:
      ...
  ```

### Translations

- Use **i18next** for all UI text -- never hardcode strings
- Save translations in `frontend/public/locales/[language].json`
- Use translation keys: `t("key.path")` instead of plain text
