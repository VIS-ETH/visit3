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

Install frontend dependencies when you want to run the frontend outside Docker:

```bash
cd frontend && yarn install
```

Generate backend gRPC stubs and frontend Orval clients:

```bash
make
```

Start the full dev stack:

```bash
docker compose --profile frontend up --build
```

This starts FastAPI, the Vite frontend, PostgreSQL, rclone S3, Keycloak, and the Notifications API.

The backend dev container mounts `backend/app`, `backend/migrations`, `backend/scripts`, and `backend/alembic.ini`, so changes in application code, migrations, and local scripts are picked up without rebuilding. The frontend dev container mounts `frontend/src`, `frontend/public`, and `frontend/scripts` for hot reload and script checks. Rebuild when changing dependency or container inputs such as `pyproject.toml`, `uv.lock`, `package.json`, `yarn.lock`, `.yarnrc.yml`, `vite.config.ts`, `tsconfig*.json`, `index.html`, or dev Dockerfiles.

Open http://localhost:3000.

To run only backend services and use a local frontend:

```bash
docker compose up --build
cd frontend && yarn dev
```

The local frontend path requires `cd frontend && yarn install` first.

## Common Commands

```bash
make                  # generate gRPC + Orval code
make DOCKER=true      # generate code in Docker containers
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

Docker Compose starts the backend, PostgreSQL, rclone S3, Keycloak, and the Notifications API. With the `frontend` profile, it also starts the Vite frontend.

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
- `app/services/` contains business logic and explicit authorization checks
- `app/repositories/` handles database access

Migrations run automatically when the backend container starts.

```bash
docker compose exec backend alembic revision --autogenerate -m "description"
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
```

Seed local test data:

```bash
docker compose exec backend python scripts/seed_test_data.py
```

## Frontend

Run in Docker:

```bash
docker compose --profile frontend up --build
```

Only `src`, `public`, and `scripts` are mounted into the Docker frontend container. This keeps package manager artifacts container-owned and avoids host/container dependency drift, but it means config and dependency changes need a rebuild.

Run locally against the Docker backend:

```bash
docker compose up --build
cd frontend && yarn dev
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
