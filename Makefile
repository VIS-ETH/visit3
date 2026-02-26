DOCS_FILE = ./frontend/src/orval

PYTHON_BACKEND = ./backend/.venv/bin/python

PROTOS_DST = ./backend/app/generated
PROTOS_PREFIX = app.generated

PROTOS := $(shell find ./servis -name "*.proto" -not -path "./servis/google/*")

.PHONY: generate clean

generate:
	$(MAKE) generate-grpc
	$(MAKE) generate-orval

clean:
	$(MAKE) clean-grpc
	$(MAKE)	clean-orval

generate-grpc:
	$(MAKE) clean-grpc
	rm -rf $(PROTOS_DST)
	mkdir $(PROTOS_DST)
	uv sync --project backend
	$(PYTHON_BACKEND) -m grpc_tools.protoc \
    -I ./servis \
    --python_out=pyi_out:$(PROTOS_DST) \
    --grpc_python_out=$(PROTOS_DST) \
    $(PROTOS)

	find $(PROTOS_DST) -type d -exec touch {}/__init__.py \;
	./scripts/fix_imports.sh $(PROTOS_DST) $(PROTOS_PREFIX)

clean-grpc:
	rm -rf $(PROTOS_DST)

generate-orval:
	$(MAKE) clean-orval
	uv sync --project backend
	$(PYTHON_BACKEND) ./scripts/extract_docs.py $(DOCS_FILE)/visit.json
	cd frontend && ./node_modules/.bin/orval --config src/orval/orvalConfig.ts

clean-orval:
	rm -rf $(DOCS_FILE)/generated $(DOCS_FILE)/visit.json
