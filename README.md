# VISIT 3

Company portal for VIS. The frontend is React + Mantine; the backend is FastAPI.

## AI Disclaimer

This README is mostly LLM generated.

## Setup

Prerequisites:

- [Docker Engine / Docker Desktop](https://docs.docker.com/get-docker/)
- [mise](https://mise.jdx.dev/) for Node, uv, yarn, and `prek`

Install tools and Git hooks:

```bash
mise install
```

Install frontend dependencies:

```bash
cd frontend && yarn install
```

Generate backend gRPC stubs and frontend Orval clients:

```bash
make
```

Start backend services:

```bash
docker compose up --build
```

Run the frontend locally:

```bash
cd frontend && yarn dev
```

Open http://localhost:3000.

## Common Commands

```bash
make                  # generate gRPC + Orval code
make clean            # remove generated artifacts
make check            # backend + frontend lint, typecheck, and i18n checks
make lint             # backend and frontend linters
make typecheck        # backend pyright and frontend tsc -b
make backend-check    # backend lint + typecheck
make frontend-check   # frontend lint + typecheck + i18n checks
prek run --all-files  # run Git hooks manually
```

Frontend-only:

```bash
cd frontend
yarn check:all
yarn typecheck
yarn build
```

The default backend checks cover application code. Use the stricter targets when you intentionally want generated files, migrations, or scripts included:

```bash
make backend-lint-all
make backend-typecheck-all
```

## Services

Docker Compose starts the backend, PostgreSQL, MinIO, Keycloak, and the Notifications API.

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MinIO | http://localhost:9000 |
| Keycloak | http://localhost:8181 |
| Notifications API | http://localhost:6781 |
| PostgreSQL | localhost:5432 |

## Backend

The backend follows `routes -> services -> repositories`.

- `app/routes/` handles HTTP concerns
- `app/services/` contains business logic and authorization decorators
- `app/repositories/` handles database access

Migrations run automatically when the backend container starts.

```bash
docker compose exec backend alembic revision --autogenerate -m "description"
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
```

Seed local test data:

```bash
docker compose exec backend sh -lc "cd /app && /opt/venv/bin/python scripts/seed_test_data.py"
```

## Frontend

Run locally:

```bash
cd frontend && yarn dev
```

Run in Docker:

```bash
docker compose --profile frontend up --build
```

Use meaningful FastAPI `operation_id`s because Orval uses them for generated client function names.

## Translations

- Use i18next keys for UI text; do not hardcode user-facing strings.
- Locale files live in `frontend/public/locales/[language]/`.
- Current namespaces: `common`, `auth`, `account`, `admin`, `kp`.
- Shared labels and validation copy belong in `common.json`; feature copy belongs in the feature namespace.
- Zod validation messages are translation keys too, for example `z.email("email.valid")` and `.min(1, "validation.required")`.

Useful checks:

```bash
cd frontend
yarn check:i18n-keys
yarn check:i18n-literals
```

`check:i18n-keys` scans `frontend/src`, schema validation messages, and split namespace files. It also verifies that EN and DE expose the same full key set.

Translation JSON are LLM-generated. Review generated copy for obvious mistakes before committing.
