DOCS_FILE = ./frontend/src/orval

PYTHON_BACKEND = ./backend/.venv/bin/python
PYTHON_CODEGEN_IMAGE = python:3.12-slim
NODE_CODEGEN_IMAGE = node:24
DOCKER_RUN = docker run --rm -v $(CURDIR):/repo -w /repo
DOCKER_UV = apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/* && curl -LsSf https://astral.sh/uv/0.11.6/install.sh | sh && export PATH="$$HOME/.local/bin:$$PATH"

PROTOS_DST = ./backend/app/generated
PROTOS_PREFIX = app.generated

PROTOS := $(shell find ./servis -name "*.proto" -not -path "./servis/google/*")

.PHONY: generate clean check lint typecheck frontend-check frontend-lint frontend-typecheck frontend-i18n backend-check backend-lint backend-lint-all backend-typecheck backend-typecheck-all

generate:
	$(MAKE) generate-grpc
	$(MAKE) generate-orval

clean:
	$(MAKE) clean-grpc
	$(MAKE)	clean-orval

check:
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) frontend-i18n

lint:
	$(MAKE) backend-lint
	$(MAKE) frontend-lint

typecheck:
	$(MAKE) backend-typecheck
	$(MAKE) frontend-typecheck

frontend-check:
	$(MAKE) frontend-lint
	$(MAKE) frontend-typecheck
	$(MAKE) frontend-i18n

frontend-lint:
	cd frontend && yarn lint

frontend-typecheck:
	cd frontend && yarn tsc -b

frontend-i18n:
	cd frontend && yarn check:i18n-keys
	cd frontend && yarn check:i18n-literals

backend-check:
	$(MAKE) backend-lint
	$(MAKE) backend-typecheck

backend-lint:
	cd backend && uv run ruff check app

backend-typecheck:
	cd backend && uv run pyright

backend-lint-all:
	uv run --project backend ruff check backend

backend-typecheck-all:
	cd backend && uv run pyright .

generate-grpc:
	$(MAKE) clean-grpc
	rm -rf $(PROTOS_DST)
	mkdir $(PROTOS_DST)
ifeq ($(DOCKER),true)
	$(DOCKER_RUN) $(PYTHON_CODEGEN_IMAGE) sh -lc '\
		$(DOCKER_UV) && \
		uv sync --project backend && \
		backend/.venv/bin/python -m grpc_tools.protoc \
			-I ./servis \
			--python_out=pyi_out:$(PROTOS_DST) \
			--grpc_python_out=$(PROTOS_DST) \
			$(PROTOS) && \
		find $(PROTOS_DST) -type d -exec touch {}/__init__.py \; && \
		backend/.venv/bin/python ./scripts/fix_imports.py $(PROTOS_DST) $(PROTOS_PREFIX)'
else
	uv sync --project backend
	$(PYTHON_BACKEND) -m grpc_tools.protoc \
    -I ./servis \
    --python_out=pyi_out:$(PROTOS_DST) \
    --grpc_python_out=$(PROTOS_DST) \
    $(PROTOS)

	find $(PROTOS_DST) -type d -exec touch {}/__init__.py \;
	${PYTHON_BACKEND} ./scripts/fix_imports.py $(PROTOS_DST) $(PROTOS_PREFIX)
endif

clean-grpc:
	rm -rf $(PROTOS_DST)

generate-orval:
	$(MAKE) clean-orval
ifeq ($(DOCKER),true)
	$(DOCKER_RUN) $(PYTHON_CODEGEN_IMAGE) sh -lc '\
		$(DOCKER_UV) && \
		uv sync --project backend && \
		backend/.venv/bin/python ./scripts/extract_docs.py $(DOCS_FILE)/visit.json'
	$(DOCKER_RUN) $(NODE_CODEGEN_IMAGE) sh -lc '\
		corepack enable && \
		cd frontend && \
		yarn install --frozen-lockfile && \
		./node_modules/.bin/orval --config src/orval/orvalConfig.ts'
else
	uv sync --project backend
	$(PYTHON_BACKEND) ./scripts/extract_docs.py $(DOCS_FILE)/visit.json
	cd frontend && ./node_modules/.bin/orval --config src/orval/orvalConfig.ts
endif

clean-orval:
	rm -rf $(DOCS_FILE)/generated $(DOCS_FILE)/visit.json
