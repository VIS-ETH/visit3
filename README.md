# VISIT 3

## The new company portal for VIS

The frontend is React with Mantine and the backend is FastAPI.

## Table of Contents

- [Setup](#setup)
  - [Quick Start](#quick-start)
  - [Dependencies](#dependencies)
  - [Development workflow](#development-workflow)
  - [Backend](#backend)
  - [Frontend](#frontend)
  - [Frontend (Docker)](#frontend-docker)
- [Database Migrations](#database-migrations)
- [Test Data Seeding](#test-data-seeding)
- [Important Bits](#important-bits)

## Setup

### Quick Start

1. Open the repository in the VS Code dev container.
2. In a terminal **inside the dev container**, run code generation:

```bash
make
```

3. In a terminal on your **host machine** (outside the dev container), start backend + infra services:

```bash
docker compose up --build
```

4. In a terminal **inside the dev container**, start the frontend:

```bash
cd frontend
yarn dev
```

5. Open http://localhost:3000.

### Dependencies

Download these before running the project.

- [uv](https://docs.astral.sh/uv/)
- [yarn](https://yarnpkg.com/)
- [Docker Engine / Docker Desktop](https://docs.docker.com/get-docker/)

### Development workflow

Use a split workflow for local development:

- **Frontend**: run inside the VS Code dev container
- **Backend + infrastructure services**: run outside the dev container (from your host terminal)

If you are new to this setup, see [What are Development Containers?](https://code.visualstudio.com/docs/devcontainers/containers).

### Code Generation

Run this first. It updates both backend and frontend generated artifacts (gRPC + Orval).

Run this from a terminal **inside the dev container**:

```bash
# Run this in project root
make
```

### Backend

The Docker Compose file starts backend, MinIO, Keycloak, Notifications API, and PostgreSQL.

Run this from your **host terminal** (outside the dev container):

```bash
# Run this in project root
docker compose up --build
```

If you want the frontend container too, enable the profile:

```bash
docker compose --profile frontend up --build
```

The backend is set up so simple changes reload automatically. For some complex changes, restart the backend container.

When the backend is up, you can open http://localhost:8000/docs for the auto-generated OpenAPI docs.

**Services:**

- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Minio (S3): http://localhost:9000
- Minio Console: http://localhost:9001
- Keycloak (Auth): http://localhost:8181
- Notifications API: http://localhost:6781
- Database: localhost:5432

### Frontend

Run this from a terminal **inside the dev container**:

```bash
# Starts the frontend
cd frontend
yarn dev
```

Then go to http://localhost:3000 to access the frontend.

### Frontend (Docker)

Running the frontend in Docker is **not recommended** for daily development because rebuilds are slower and hot reload is limited. Use it when you want production parity or full stack integration testing.

If you are using the dev container workflow above, prefer `yarn dev` inside the dev container instead.

```bash
# Run this in project root
docker compose --profile frontend up --build
```

The container serves the frontend at http://localhost:3000.

## Database Migrations

The backend uses Alembic for database migrations. When you start the backend with Docker, migrations are automatically applied.

To create a new migration after model changes:

```bash
# In the running backend container (host terminal)
docker compose exec backend alembic revision --autogenerate -m "description of migration"
```

To apply pending migrations manually:

```bash
# In the running backend container (host terminal)
docker compose exec backend alembic upgrade head
```

To revert to a previous migration:

```bash
# In the running backend container (host terminal)
docker compose exec backend alembic downgrade -1
```

If you run migrations from a local Python environment instead, make sure env vars in `backend/.env` point to reachable hosts (not Compose service names).

## Test Data Seeding

You can seed demo users and companies directly inside the running backend container.

```bash
# Run this in project root from host terminal (backend service must be running)
docker compose exec backend sh -lc "cd /app && .venv/bin/python scripts/seed_test_data.py"
```

The seed script creates/updates test records for:

- Unconfirmed company users
- Staff users
- Admin users
- Confirmed company users

The script is idempotent for its email pool, so running it again updates existing seeded users instead of duplicating them.

## Important Bits

### Code Formatting

- **Backend**: Use [Black](https://github.com/psf/black) for Python code formatting
- **Frontend**: Use [Prettier](https://prettier.io/) for code formatting

### API Routes & Types

- Ensure FastAPI routes are **properly typed** with return types and request body schemas
- Use **meaningful route names** - Orval uses these to generate client code
- Example:
  ```python
  @router.post("/login", operation_id="login")
  async def login(request: LoginRequest) -> TokenResponse:
      ...
  ```

### Translations

- Use **i18next** for all UI text - never hardcode strings
- Save translations in `frontend/public/locales/[language].json`
- Always use translation keys: `t("key.path")` instead of plain text
