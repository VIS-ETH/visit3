API_URL = http://localhost:8000/openapi.json
DOCS_FILE = ./frontend/src/orval/

.PHONY: generate clean

generate:
	${MAKE} clean 
	docker compose up --build -d

	@until curl -s --fail $(API_URL) > /dev/null; do \
		printf '.'; \
		sleep 1; \
	done
	
	curl -s $(API_URL) > $(DOCS_FILE)/visit.json
	npx orval --config $(DOCS_FILE)/orvalConfig.ts

	docker compose down

clean:
	rm -rf $(DOCS_FILE)/generated $(DOCS_FILE)/visit.json