# VISIT 3

Company portal for VIS. The frontend is React + Mantine; the backend is FastAPI.

## AI Disclaimer

This README is mostly LLM generated.

## Setup

Prerequisites:

- [Docker Engine / Docker Desktop](https://docs.docker.com/get-docker/)
- [mise](https://mise.jdx.dev/) for Node, uv, and `prek`

Install tools and Git hooks:

```bash
mise install
```

Create the local environment files from the committed examples and replace the
placeholder secrets before deploying anything:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Before starting the backend, configure the shared `SIP_AUTH_OIDC_*` client and notification
endpoint described in the Backend section below. The local plaintext
notification service requires `NOTIFICATION_API_TLS=false`.

Yarn is managed by Corepack from `frontend/package.json`.

Install frontend dependencies when you want to run the frontend outside Docker:

```bash
cd frontend && corepack enable && yarn install
```

Generate backend gRPC stubs and frontend Orval clients:

```bash
make
```

Start the full dev stack:

```bash
docker compose --profile frontend up --build
```

This starts FastAPI, the Vite frontend, PostgreSQL, rclone S3, Keycloak, and the Notifications API. PostgreSQL keeps its cluster in `data/postgres`; existing local data in `data/sql` was written by Postgres 17 and is not migrated, so dump and restore it or delete it.

The backend dev container mounts `backend/app`, `backend/migrations`, `backend/scripts`, and `backend/alembic.ini`, so changes in application code, migrations, and local scripts are picked up without rebuilding. The frontend dev container mounts `frontend/src`, `frontend/public`, and `frontend/scripts` for hot reload and script checks. Rebuild when changing dependency or container inputs such as `pyproject.toml`, `uv.lock`, `package.json`, `yarn.lock`, `.yarnrc.yml`, `vite.config.ts`, `tsconfig*.json`, `index.html`, or dev Dockerfiles.

Open http://localhost:3000.

To run only backend services and use a local frontend:

```bash
docker compose up --build
cd frontend && yarn dev
```

The local frontend path requires `cd frontend && yarn install` first.
If Corepack is not enabled yet, run `cd frontend && corepack enable && yarn install`.

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

Application-to-application authentication uses OAuth 2.0 client credentials.
Configure these required backend environment variables before starting the app:

- `SIP_AUTH_OIDC_TOKEN_ENDPOINT`: the shared HTTPS token endpoint, without URL credentials, query, or fragment.
- `SIP_AUTH_OIDC_CLIENT_ID`: the existing registered OIDC client, with service accounts enabled.
- `SIP_AUTH_OIDC_CLIENT_SECRET`: that client's secret, supplied through the existing environment/secret mechanism.
- `NOTIFICATION_API_URL`: the separate notification API host and port.

`NOTIFICATION_SENDER_EMAIL` defaults to `visit@vis.ethz.ch` and is explicitly
included as the sender on outgoing mail. It is separate from
`DEFAULT_NOTIFICATION_EMAIL`, which controls the staff notification recipient.
In Keycloak, grant the application's service account the notification API client
role `mail` as well as `mail-sender:visit@vis.ethz.ch` (or the configured sender).
Both roles must appear under the notification API's client in the issued access
token. A sender role alone does not grant permission to send mail.

`NOTIFICATION_API_TLS=true` (the default) enables TLS with certificate and hostname
verification. For an internal plaintext gRPC listener, explicitly set
`NOTIFICATION_API_TLS=false`. OAuth bearer authentication stays enabled in both
modes. Plaintext mode sends bearer tokens unencrypted on that connection unless
the infrastructure supplies encryption; use it only for the intended internal
service. TLS handshake failures never trigger an automatic plaintext fallback. `NOTIFICATION_API_CA_FILE` can point to a trusted
private CA for the notification service. The HTTPS token client uses normal
system/environment CA configuration supported by HTTPX.

The backend obtains its first token during startup, then a connection-level gRPC
interceptor authenticates every notification RPC, including scheduled mail.
[Authlib](https://docs.authlib.org/en/v1.7.0/oauth2/client/http/index.html) manages
in-memory token caching and renewal using the token response's expiry and a
five-second renewal margin, so short-lived tokens are reused. Opaque access
tokens work too. Token responses must contain a bearer `access_token` and expiry
(`expires_in` or `expires_at`). Responses are validated before replacing the
cached token; an invalid renewal fails that request and allows the next request
to retry. Client authentication tries HTTP Basic,
then request-body credentials if client authentication is rejected, and reuses
the selected method. No scopes, audiences, resource parameters, interactive login,
or ID tokens are requested. Token acquisition failures stop startup or propagate
to the caller without logging response bodies or credentials. Clients close on
shutdown and failed startup.

Register this application for the client-credentials grant with the authorization
server, configure its resource mappers for the intended downstream API, and grant
the required API permissions in the deployment. The receiving API must validate
tokens and enforce authorization independently; obtaining a token does not prove
access. This repository currently connects only to the notification gRPC API.
If another API is added, share this lifecycle-owned token source only if the
issued token is authorized for both targets.

User login and mail authentication share these client credentials and token
endpoint. Login uses the authorization-code grant; mail uses the client-credentials
grant and gets its own service-account access token. No separate `OAUTH_*` or
`SIP_MAILAPI_SA_*` variables are needed.
The service-account requirements are validated at application startup, even with
`DEBUG=true`, using the values already loaded by the existing settings mechanism.
Schema generation does not start the application lifecycle and requires neither
real client credentials nor network access. The example environment intentionally
leaves the shared client secret blank.
For the bundled plaintext Compose notification service, set
`NOTIFICATION_API_URL=notifications-api:6781` and `NOTIFICATION_API_TLS=false`.
The backend still requires an HTTPS authorization server and service-account
credentials at startup, even when the local notification server does not enforce
authentication. The notification transport setting does not disable HTTPS
verification for the token endpoint. Unit tests use local mocks and need no
external credentials. The local gRPC TLS tests additionally check bearer delivery
and rejection of untrusted certificates and incorrect hostnames.

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
