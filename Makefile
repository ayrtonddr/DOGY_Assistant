.PHONY: install sync lock test lint doctor chat-es chat-en audit
install sync:
	uv sync --group dev
lock:
	uv lock
test:
	uv run pytest -q
lint:
	uv run ruff check .
doctor:
	uv run dogy doctor
chat-en:
	uv run dogy chat --lang en --timezone America/Mexico_City
chat-es:
	uv run dogy chat --lang es --timezone America/Mexico_City
audit:
	uv run dogy verify-audit
