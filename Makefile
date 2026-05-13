DOCS_FILE = ./frontend/src/orval

PYTHON_BACKEND = ./backend/.venv/bin/python
PYTHON_CODEGEN_IMAGE = python:3.12-slim
NODE_CODEGEN_IMAGE = node:24
DOCKER_RUN = docker run --rm -v $(CURDIR):/repo -v /repo/backend/.venv -v /repo/frontend/node_modules -v /repo/frontend/.yarn -w /repo
DOCKER_UV = apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/* && curl -LsSf https://astral.sh/uv/0.11.6/install.sh | sh && export PATH="$$HOME/.local/bin:$$PATH"
UV_SYNC_BACKEND_CODEGEN = uv sync --project backend --group codegen
COMPILE_GRPC_PROTOS = $(PYTHON_BACKEND) -m grpc_tools.protoc -I ./servis --python_out=pyi_out:$(PROTOS_DST) --grpc_python_out=$(PROTOS_DST) $(PROTOS)
FIX_GRPC_IMPORTS = find $(PROTOS_DST) -type d -exec touch {}/__init__.py \; && $(PYTHON_BACKEND) ./scripts/fix_imports.py $(PROTOS_DST) $(PROTOS_PREFIX)
EXTRACT_OPENAPI_DOCS = $(UV_SYNC_BACKEND_CODEGEN) && $(PYTHON_BACKEND) ./scripts/extract_docs.py $(DOCS_FILE)/visit.json
GENERATE_ORVAL_CLIENT = cd frontend && corepack enable && yarn install --immutable && yarn orval --config src/orval/orvalConfig.ts

PROTOS_DST = ./backend/app/generated
PROTOS_PREFIX = app.generated

PROTOS := $(shell find ./servis -name "*.proto" -not -path "./servis/google/*")

.PHONY: generate clean check lint typecheck frontend-check frontend-lint frontend-typecheck frontend-i18n backend-check backend-lint backend-lint-all backend-typecheck backend-typecheck-all generate-grpc clean-grpc generate-orval clean-orval

generate:
	$(MAKE) generate-grpc
	$(MAKE) generate-orval

clean: clean-grpc clean-orval

check: lint typecheck frontend-i18n

lint: backend-lint frontend-lint

typecheck: backend-typecheck frontend-typecheck

frontend-check: frontend-lint frontend-typecheck frontend-i18n

frontend-lint:
	cd frontend && yarn lint

frontend-typecheck:
	cd frontend && yarn tsc -b

frontend-i18n:
	cd frontend && yarn check:i18n-keys
	cd frontend && yarn check:i18n-literals

backend-check: backend-lint backend-typecheck

backend-lint:
	cd backend && uv run ruff check app

backend-typecheck:
	cd backend && uv run pyright

backend-lint-all:
	uv run --project backend ruff check backend

backend-typecheck-all:
	cd backend && uv run pyright .

generate-grpc: clean-grpc
	mkdir -p $(PROTOS_DST)
ifeq ($(DOCKER),true)
	$(DOCKER_RUN) $(PYTHON_CODEGEN_IMAGE) sh -lc '\
			$(DOCKER_UV) && \
			$(UV_SYNC_BACKEND_CODEGEN) && \
			$(COMPILE_GRPC_PROTOS) && \
			$(FIX_GRPC_IMPORTS)'
else
	$(UV_SYNC_BACKEND_CODEGEN)
	$(COMPILE_GRPC_PROTOS)
	$(FIX_GRPC_IMPORTS)
endif

clean-grpc:
	rm -rf $(PROTOS_DST)

generate-orval: clean-orval
ifeq ($(DOCKER),true)
	$(DOCKER_RUN) $(PYTHON_CODEGEN_IMAGE) sh -lc '\
		$(DOCKER_UV) && \
		$(EXTRACT_OPENAPI_DOCS)'
	$(DOCKER_RUN) $(NODE_CODEGEN_IMAGE) sh -lc '\
			$(GENERATE_ORVAL_CLIENT)'
else
	$(EXTRACT_OPENAPI_DOCS)
	$(GENERATE_ORVAL_CLIENT)
endif

clean-orval:
	rm -rf $(DOCS_FILE)/generated $(DOCS_FILE)/visit.json
