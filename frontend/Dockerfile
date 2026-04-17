# Stage 1: Generate gRPC stubs and OpenAPI spec
FROM python:3.12-slim AS code-generator

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y perl && rm -rf /var/lib/apt/lists/*

ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /repo

COPY --from=common backend/pyproject.toml backend/uv.lock ./backend/
RUN uv sync --frozen --no-dev --project ./backend

COPY --from=common servis ./servis
COPY --from=common scripts/fix_imports.sh ./scripts/fix_imports.sh
RUN chmod +x ./scripts/fix_imports.sh

COPY --from=common backend/app ./backend/app
RUN mkdir -p ./backend/app/generated
RUN /opt/venv/bin/python -m grpc_tools.protoc \
    -I ./servis \
    --python_out=pyi_out:./backend/app/generated \
    --grpc_python_out=./backend/app/generated \
    $(find ./servis -name "*.proto" -not -path "./servis/google/*")
RUN find ./backend/app/generated -type d -exec touch {}/__init__.py \;
RUN ./scripts/fix_imports.sh ./backend/app/generated app.generated

COPY --from=common scripts/extract_docs.py ./scripts/extract_docs.py
COPY --from=common backend/.env ./backend/.env
RUN /opt/venv/bin/python ./scripts/extract_docs.py /repo/visit.json


# Build stage
FROM node:24-alpine AS builder

WORKDIR /app/frontend

COPY package.json yarn.lock ./
RUN npm install yarn && yarn

COPY tsconfig*.json vite.config.ts eslint.config.js index.html ./
COPY public public
COPY src src

COPY --from=code-generator /repo/visit.json ./src/orval/visit.json
RUN ./node_modules/.bin/orval --config src/orval/orvalConfig.ts

# Enable Vite plugin to allow handling environment variables via nginx at runtime
# See vite.config.ts
ENV REPLACE_ENV_FORMAT_ENVSUBST=true
ENV NODE_ENV=production
RUN yarn build

FROM nginx:1.29-alpine AS production

COPY --from=builder /app/frontend/dist /usr/share/nginx/html
COPY --from=builder /app/frontend/dist/index.html /usr/share/nginx/templates/index.html.template

ENV NGINX_ENVSUBST_TEMPLATE_DIR=/usr/share/nginx/templates
ENV NGINX_ENVSUBST_OUTPUT_DIR=/usr/share/nginx/html

COPY <<EOF /etc/nginx/conf.d/default.conf
server {
  listen 3000;
  server_name localhost;

  location / {
    root /usr/share/nginx/html;
    try_files \$uri /index.html;
  }
}
EOF

EXPOSE 3000
