.PHONY: docker-smoke

# Smoke-test a running docker compose stack.
# Usage: docker compose up --build -d && make docker-smoke && docker compose down
docker-smoke:
	python -c "\
import urllib.request, sys; \
resp = urllib.request.urlopen('http://localhost:8000/health/live'); \
assert resp.status == 200, f'health check failed: {resp.status}'; \
print('smoke: /health/live OK')"
