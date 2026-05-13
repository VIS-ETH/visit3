FROM python:3.12-slim AS grpc-generator

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT="/opt/gen-venv"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /build

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --group codegen --no-install-project

COPY --from=common servis ./servis
COPY --from=common scripts/fix_imports.py ./fix_imports.py

RUN mkdir -p app/generated
RUN /opt/gen-venv/bin/python -m grpc_tools.protoc \
    -I ./servis \
    --python_out=pyi_out:app/generated \
    --grpc_python_out=app/generated \
    $(find ./servis -name "*.proto" -not -path "./servis/google/*")
RUN find app/generated -type d -exec touch {}/__init__.py \;
RUN /opt/gen-venv/bin/python ./fix_imports.py app/generated app.generated


FROM python:3.12-slim AS compiler

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runner
WORKDIR /app/
COPY --from=compiler /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

COPY alembic.ini pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY --from=grpc-generator /build/app/generated ./app/generated

RUN python -m compileall -q app migrations

CMD ["sh", "-c", "alembic upgrade head && fastapi run --host 0.0.0.0 --port 8000"]
